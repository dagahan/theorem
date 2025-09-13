# src/services/synonyms_service.py
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Dict, Iterable, List, Set, Tuple

from src.services.text_normalize_service import TextNormalizeService


class SynonymService:
    def __init__(self) -> None:
        self.norm = TextNormalizeService()
        self.word_tokenizer = re.compile(r"[A-Za-zА-Яа-я0-9№%]+", re.UNICODE)
        self.whitespace_normalizer = re.compile(r"\s+")
        self.year_pattern = re.compile(r"\b(19|20)\d{2}\b")
        self.case_variants = (str.lower, str.upper, str.title)
        self.word_joiners = (" ", "-", "_", "")
        self.punctuation_separators = (" ", "-", "_", "/")
        self.adjective_endings = ("", "ый", "ий", "ая", "ое", "ые", "ого", "ему", "ому", "ым", "ими", "ых")
        self.noun_endings = ("", "а", "я", "ы", "и", "ам", "ям", "ами", "ями", "ах", "ях", "у", "ю", "ой", "ей", "ов", "ев")
        self.synonym_database: Dict[str, List[str]] = self._initialize_synonym_database()
        self.russian_to_latin_map = self._create_russian_to_latin_mapping()
        self.latin_to_russian_map = {v: k for k, v in self.russian_to_latin_map.items()}
        self.keyboard_layout_ru_to_en, self.keyboard_layout_en_to_ru = self._create_keyboard_layout_mappings()
        self.max_expansions_per_word = 300
        self.max_query_length = 4000


    def extract_words(
        self,
        text: str
    ) -> List[str]:
        return [m.group(0).lower() for m in self.word_tokenizer.finditer(text.lower())]


    def expand_query_variants(
        self,
        queries: List[str]
    ) -> List[str]:
        expanded_queries: List[str] = []

        for query in queries:
            normalized_query = self.norm.normalize_chunk_text(query)
            query_words = self.extract_words(normalized_query)
            expanded_words = self.generate_word_variants(query_words)
            expanded_text = " ".join(expanded_words)[: self.max_query_length]
            expanded_queries.append((normalized_query + " " + expanded_text).strip())

        return expanded_queries


    def generate_word_variants(
        self,
        words: Iterable[str]
    ) -> List[str]:
        unique_variants: Set[str] = set()
        variant_list: List[str] = []

        for word in words:
            for variant in self._generate_word_expansions(word)[: self.max_expansions_per_word]:
                if variant not in unique_variants:
                    unique_variants.add(variant)
                    variant_list.append(variant)
                    
        return variant_list


    def add_synonym_group(
        self,
        main_term: str,
        synonyms: Iterable[str]
    ) -> None:
        normalized_term = main_term.lower().strip()
        existing_synonyms = self.synonym_database.get(normalized_term, [])
        merged_synonyms = list(dict.fromkeys(existing_synonyms + [s for s in synonyms if s]))
        self.synonym_database[normalized_term] = merged_synonyms


    def import_synonym_dictionary(
        self,
        additional_synonyms: Dict[str, Iterable[str]]
    ) -> None:
        for term, synonyms in additional_synonyms.items():
            self.add_synonym_group(term, synonyms)


    def _generate_word_expansions(
        self,
        word: str
    ) -> List[str]:
        return list(self._expand_word_variants(word))


    def _expand_word_variants(
        self,
        word: str
    ) -> Iterable[str]:
        cleaned_word = word.strip()
        if not cleaned_word:
            return
        cleaned_word = self.whitespace_normalizer.sub(" ", cleaned_word)
        yield from self._remove_duplicates(
            cleaned_word,
            *self._get_database_synonyms(cleaned_word),
            *self._generate_case_variants(cleaned_word),
            *self._generate_hyphen_variants(cleaned_word),
            *self._generate_year_variants(cleaned_word),
            *self._generate_transliteration_variants(cleaned_word),
            *self._generate_keyboard_layout_variants(cleaned_word),
            *self._generate_morphological_variants(cleaned_word),
            *self._generate_symbol_variants(cleaned_word),
        )


    def _get_database_synonyms(
        self,
        word: str
    ) -> List[str]:
        normalized_word = word.lower()
        synonyms = self.synonym_database.get(normalized_word, [])
        return list(synonyms)


    def _generate_case_variants(
        self,
        text: str
    ) -> List[str]:
        return list({case_function(text) for case_function in self.case_variants})


    def _generate_hyphen_variants(
        self,
        text: str
    ) -> List[str]:
        word_parts = [part for part in self.whitespace_normalizer.split(text) if part]
        if len(word_parts) <= 1:
            return [text]

        variants: Set[str] = set()

        for joiner in self.word_joiners:
            variants.add(joiner.join(word_parts))

        return list(variants)


    def _generate_year_variants(
        self,
        text: str
    ) -> List[str]:
        year_matches = self.year_pattern.findall(text)
        if not year_matches:
            return []

        year_variants: Set[str] = set()

        for separator in self.punctuation_separators:
            year_variants.add(self.year_pattern.sub(lambda match: f"{separator}{match.group(0)}", text))
            year_variants.add(self.year_pattern.sub(lambda match: f"{match.group(0)}{separator}", text))

        return list(year_variants)


    def _generate_transliteration_variants(
        self,
        text: str
    ) -> List[str]:
        cyrillic_version = self._convert_to_cyrillic(text)
        latin_version = self._convert_to_latin(text)
        transliteration_variants = {cyrillic_version, latin_version}

        for case_function in self.case_variants:
            transliteration_variants.add(case_function(cyrillic_version))
            transliteration_variants.add(case_function(latin_version))

        return list(transliteration_variants)


    def _generate_keyboard_layout_variants(
        self,
        text: str
    ) -> List[str]:
        english_layout = "".join(self.keyboard_layout_ru_to_en.get(char, char) for char in text)
        russian_layout = "".join(self.keyboard_layout_en_to_ru.get(char, char) for char in text)
        return list({english_layout, russian_layout})


    def _generate_morphological_variants(
        self,
        word: str
    ) -> List[str]:
        word_stem = self._extract_word_stem(word)
        morphological_variants: Set[str] = set()

        for adjective_ending in self.adjective_endings:
            morphological_variants.add(word_stem + adjective_ending)

        for noun_ending in self.noun_endings:
            morphological_variants.add(word_stem + noun_ending)

        return list(morphological_variants)


    def _generate_symbol_variants(
        self,
        text: str
    ) -> List[str]:
        normalized_symbols = text.replace("№", "No").replace("no", "No").replace("%", " percent ")
        return list({normalized_symbols, normalized_symbols.replace(" ", ""), normalized_symbols.replace(" ", "-")})


    def _convert_to_latin(
        self,
        text: str
    ) -> str:
        latin_chars = []
        for char in unicodedata.normalize("NFKC", text):
            lowercase_char = char.lower()
            latin_chars.append(self.russian_to_latin_map.get(lowercase_char, char))
        return "".join(latin_chars)


    def _convert_to_cyrillic(
        self,
        text: str
    ) -> str:
        cyrillic_chars = []
        position = 0

        while position < len(text):
            two_char_chunk = text[position : position + 2].lower()
            single_char = text[position].lower()
            mapped_char = None

            for cyrillic_char, latin_chars in self.russian_to_latin_map.items():
                if isinstance(latin_chars, str) and len(latin_chars) == 2 and latin_chars == two_char_chunk:
                    mapped_char = cyrillic_char
                    position += 2
                    break

            if mapped_char is None:
                mapped_char = next((cyrillic_char for cyrillic_char, latin_chars in self.russian_to_latin_map.items() if latin_chars == single_char), text[position])
                position += 1
            cyrillic_chars.append(mapped_char)

        return "".join(cyrillic_chars)


    def _extract_word_stem(
        self,
        word: str
    ) -> str:
        lowercase_word = word.lower()
        stem = re.sub(r"(ий|ый|ой|ая|ое|ые|ого|ему|ому|ыми|ими|ых|ах|ях|ам|ям|ов|ев|ой|ей|у|ю|а|я|ы|и)$", "", lowercase_word)
        return stem


    def _remove_duplicates(
        self,
        *values: str
    ) -> Iterable[str]:
        processed_values: Set[str] = set()
        for value in values:
            normalized_value = self.whitespace_normalizer.sub(" ", value).strip()
            if not normalized_value:
                continue
            if normalized_value not in processed_values:
                processed_values.add(normalized_value)
                yield normalized_value


    def _create_russian_to_latin_mapping(self) -> Dict[str, str]:
        return {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
            "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
            "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh",
            "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        }


    def _create_keyboard_layout_mappings(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        ru = "ёйцукенгшщзхъфывапролджэячсмитьбю"
        en = "`qwertyuiop[]asdfghjkl;'zxcvbnm,."
        ru2en = {r: e for r, e in zip(ru, en)}
        en2ru = {e: r for r, e in zip(ru, en)}
        ru2en.update({r.upper(): e.upper() for r, e in zip(ru, en)})
        en2ru.update({e.upper(): r.upper() for r, e in zip(ru, en)})
        return ru2en, en2ru


    @lru_cache(maxsize=8192)
    def get_cached_word_expansions(self, word: str) -> Tuple[str, ...]:
        return tuple(self._generate_word_expansions(word))


    def _initialize_synonym_database(self) -> Dict[str, List[str]]:
        return {
            "егэ": [
                "единый государственный экзамен", "единый госэкзамен", "экзамен", "гиа", "гвэ",
                "unified state exam", "ege", "егэ-2025", "егэ 2025", "егэ математика", "егэ профиль", "егэ база",
                "контрольно-измерительные материалы", "ким",
                "демоверсия егэ", "демо-вариант", "демонстрационный вариант", "образец варианта",
                "спецификация ким", "паспорт ким", "описание ким", "структура ким", "параметры варианта",
                "кодификатор егэ", "перечень требований", "элементы содержания", "кодификатор",
                "паспорт работы", "модель экзамена",
            ],
            "гия": [
                "государственная итоговая аттестация", "итоговая аттестация", "gia", "порядок проведения гиа",
                "гия-11", "гия 11 класс", "регламент проведения",
            ],
            "гвэ": [
                "государственный выпускной экзамен", "выпускной экзамен", "gve", "особенности гвэ",
                "устная форма гвэ", "письменная форма гвэ",
            ],
            "демоверсия": [
                "демо", "демонстрационный вариант", "образец варианта", "демо-вариант", "пример варианта",
            ],
            "вариант": [
                "экзаменационный вариант", "комплект ким", "тестовый вариант", "номер варианта",
            ],
            "кодификатор": [
                "кодиф", "перечень требований", "элементы содержания", "перечень тем",
                "кодификатор егэ", "структура содержания",
            ],
            "спецификация": [
                "паспорт ким", "описание ким", "структура ким", "параметры варианта", "модель экзамена",
                "паспорт работы", "спец", "спецификация ким",
            ],

            # Роли / структуры / площадки
            "фипи": [
                "федеральный институт педагогических измерений", "fipi", "банк заданий фипи",
                "открытый банк", "разработчик ким",
            ],
            "рособрнадзор": [
                "рособрнадзор", "federal service for supervision in education and science",
            ],
            "ппэ": [
                "пункт проведения экзаменов", "пункт проведения экзамена", "ppe", "exam site", "exam venue",
                "аудитория ппэ", "штаб ппэ", "офлайн-аудитория", "ппэ том", "труднодоступные и отдаленные местности",
            ],
            "рцои": [
                "региональный центр обработки информации", "rcoi", "региональный центр", "центр обработки информации",
            ],
            "гэк": [
                "государственная экзаменационная комиссия", "gek", "член гэк", "председатель гэк",
            ],
            "ак": [
                "апелляционная комиссия", "appeal commission", "комиссия по апелляциям", "форма 2-ап",
            ],
            "пк": [
                "предметная комиссия", "subject commission", "экспертная комиссия", "эксперты пк",
            ],
            "сиц": [
                "ситуационный информационный центр", "sic", "центр наблюдения", "центр мониторинга",
            ],
            "фцт": [
                "федеральный центр тестирования", "fct",
            ],
            "рис": [
                "региональная информационная система",
            ],
            "фис": [
                "федеральная информационная система",
            ],
            "пак": [
                "программно-аппаратный комплекс",
            ],
            "арм": [
                "автоматизированное рабочее место", "рабочее место", "workstation",
            ],
            "цод": [
                "центр обработки данных", "дата-центр", "data center",
            ],

            # Материалы/процессы
            "эм": [
                "экзаменационные материалы", "материалы егэ", "exam materials", "комплект эм",
                "полный комплект эм", "печать эм", "сканирование эм", "получение эм", "передача эм",
                "хранение эм", "верификация эм",
            ],
            "видеонаблюдение": [
                "cctv", "онлайн-трансляция", "камера наблюдения", "средства видеонаблюдения",
                "система видеонаблюдения", "трансляция видеосигнала", "портал наблюдения", "smotriege", "smotriege.ru",
                "ракурсы камер", "код рцои на видеозаписи", "номер аудитории на видеозаписи",
            ],
            "печатание": [
                "печать", "печать полного комплекта", "печать эм", "печать ким",
            ],
            "сканирование": [
                "сканирование эм", "сканирование бланков", "загрузка в фис", "сканирование в аудитории",
            ],
            "бланки": [
                "бланки егэ", "бланк регистрации", "бланк ответов 1", "бланк ответов 2", "бланк доп",
            ],
            "портал": [
                "портал видеонаблюдения", "портал наблюдения", "портал smotriege", "личный кабинет",
            ],
            "метка нарушения": [
                "метка нарушений", "инцидент", "нарушение", "tag нарушения",
            ],

            # Оценивание / результаты
            "критерии": [
                "рубрикатор", "схема оценивания", "уровни достижений", "критерии проверки",
            ],
            "шкала перевода": [
                "таблица перевода", "конвертация баллов", "перевод первичных в тестовые", "шкала 2025",
            ],
            "минимальный балл": [
                "проходной балл", "порог", "cut score", "минимум для зачета", "минимум для аттестации",
            ],
            "апелляция": [
                "апелляционная комиссия", "пересчет результатов", "протокол ак", "форма 2-ап", "повторная проверка",
            ],
            "результаты": [
                "итоги экзамена", "баллы", "пересчет результатов", "итоговые баллы", "оценка работы",
            ],

            # Уровни/части/структура
            "профиль": [
                "профильный уровень", "углубленный уровень", "advanced level", "проф", "математика профиль",
            ],
            "база": [
                "базовый уровень", "basic level", "базовая математика", "математика база",
            ],
            "часть 1": [
                "первая часть", "блок 1", "задания 1–13", "самопроверяемые задания",
            ],
            "часть 2": [
                "вторая часть", "блок 2", "задания 14–19", "развернутый ответ",
            ],

            # Тематика математики
            "алгебра": [
                "уравнения", "неравенства", "системы", "функции", "многочлены", "рациональные выражения",
            ],
            "геометрия": [
                "планиметрия", "стереометрия", "окружность", "углы", "площади", "объемы", "многогранники",
            ],
            "тригонометрия": [
                "тригонометрические функции", "тождество", "радианы", "градусы", "синус", "косинус", "тангенс",
            ],
            "вероятность": [
                "комбинаторика", "статистика", "случайные события", "матожидание", "дисперсия", "вероятностные задачи",
            ],
            "таблица": [
                "табл", "table", "табличные данные", "таблица значений", "таблица спецификации",
            ],
            "формула": [
                "математическая запись", "выражение", "равенство", "неравенство", "формульная запись",
            ],

            # Организация/сроки/регламенты
            "расписание": [
                "календарь егэ", "даты экзаменов", "сроки проведения", "график", "периоды проведения",
            ],
            "время": [
                "продолжительность", "длительность", "лимит времени", "тайминг", "временной регламент",
            ],
            "регламент": [
                "порядок проведения", "инструкция", "методические рекомендации", "письмо рособрнадзора",
            ],

            # Иностранные языки (устная часть)
            "устная часть": [
                "устные ответы", "станция записи устных ответов", "аудитория проведения", "аудитория подготовки",
            ],
            "иностранные языки": [
                "английский язык", "немецкий язык", "французский язык", "испанский язык", "китайский язык",
            ],
        }



