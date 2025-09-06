import os
import click
import pandas as pd
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from sentence_transformers import CrossEncoder
from langchain.text_splitter import RecursiveCharacterTextSplitter
import xml.etree.ElementTree as ET

@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('query', required=True)
def rag_pipeline(file_path, query):
    def parse_xlsx(xlsx_path):
        sheet_name = 'Для тестового прогона Enbisys'
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        expected_columns = ['Раздел руководства', 'Вопросы', 'Ответ']
        if not all(column in df.columns for column in expected_columns):
            raise ValueError("Файл не содержит ожидаемых столбцов")
        data = df[expected_columns].fillna('').replace('\n', ' ', regex=True)
        docs = data.apply(lambda row: f"{row['Раздел руководства']}: {row['Вопросы']} - {row['Ответ']}", axis=1).tolist()
        return docs
    
    def parse_wiki_dump(xml_path, min_text_length=50, max_articles=None):
        articles = []
        context = ET.iterparse(xml_path, events=("end",))
        page_count = 0
        kept_count = 0
        for event, elem in context:
            if elem.tag.endswith("page"):
                page_count += 1
                title = elem.findtext("./title")
                ns = elem.findtext("./ns")
                if ns == "0":
                    text = elem.findtext(".//text")
                    if text and len(text) >= min_text_length:
                        clean_text = text.replace('\n', ' ')
                        articles.append(f"{title}: {clean_text}")
                        kept_count += 1
                        if kept_count <= 3:  # Показываем первые 3 добавленных статьи
                            print(f"[LOG] Добавлена статья: '{title}' (длина: {len(clean_text)})")
                    else:
                        if text is not None:
                            print(f"[LOG] Пропущена статья '{title}': текст слишком короткий ({len(text)})")
                        else:
                            print(f"[LOG] Пропущена статья '{title}': нет текста")
                else:
                    print(f"[LOG] Пропущена страница '{title}': ns={ns}")
                elem.clear()
                if max_articles and kept_count >= max_articles:
                    print(f"[LOG] Достигнут лимит {max_articles} статей, остановка парсинга.")
                    break
        print(f"[LOG] Всего страниц обработано: {page_count}")
        print(f"[LOG] Статей, прошедших фильтр: {kept_count}")
        return articles

    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".xlsx":
        print("[LOG] Обнаружен Excel-файл, парсим как таблицу...")
        documents = parse_xlsx(file_path)
    elif ext.startswith(".xml"):
        print("[LOG] Обнаружен XML-файл, парсим как дамп Википедии...")
        documents = parse_wiki_dump(file_path)
    else:
        raise ValueError("Поддерживаются только файлы .xlsx и .xml")

    print(f"[LOG] Найдено документов: {len(documents)}")
    if len(documents) > 0:
        print("[LOG] Пример документа:", documents[0][:500])

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=250,
        chunk_overlap=50
    )
    combined_text = " ".join(documents)
    split_documents = text_splitter.split_text(combined_text)

    embeddings = OllamaEmbeddings(model="mahonzhan/all-MiniLM-L6-v2:latest")
    vector_store = Chroma.from_texts(split_documents, embeddings)

    llm = Ollama(model="qwen2.5:1.5b")
    prompt_template = """
    Ты - голосовой помощник в электромобиле.
    Тебе поступают вопросы, связанные с конструкцией автомобиля и управлением его функциями.
    Используй следующий фрагмент контекста, чтобы ответить на вопрос. Если ты не знаешь ответа, просто скажи, что не знаешь.
    Старайся отвечать максимально кратко, но информативно.

    Контекст: {context}

    Вопрос: {question}

    Ответ:
    """
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )

    reranker = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2')

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(),
        chain_type_kwargs={"prompt": prompt}
    )

    # query = "где указан остаток хода?"
    print("Query:", query)

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    vector_candidates = retriever.get_relevant_documents(query)

    text_candidates = []
    for doc in split_documents:
        if query.lower() in doc.page_content.lower():
            text_candidates.append(doc)

    all_candidates = [c.page_content for c in vector_candidates] + text_candidates

    seen = set()
    unique_candidates = []
    for cand in all_candidates:
        if cand not in seen:
            unique_candidates.append(cand)
            seen.add(cand)

    reranked_results = reranker.predict([(query, cand) for cand in unique_candidates])
    print("Reranked_results:", reranked_results)
    best_candidate = unique_candidates[reranked_results.argmax()]
    print("Best Candidate:", best_candidate)

    response = qa_chain.run(query=query, context=best_candidate)
    print("Response:", response)

if __name__ == '__main__':
    rag_pipeline()
