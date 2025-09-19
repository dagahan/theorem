from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Set, Tuple


class SynonymService:
    def __init__(self) -> None:
        self.word_tokenizer = re.compile(r"[A-Za-zА-Яа-я0-9№%]+", re.UNICODE)
        self.whitespace_normalizer = re.compile(r"\s+")
        self.year_pattern = re.compile(r"\b(19|20)\d{2}\b")
        self.case_variants = (str.lower, str.upper, str.title)
        self.word_joiners = (" ", "-", "_", "")
        self.punctuation_separators = (" ", "-", "_", "/")
        self.adjective_endings = ("", "ый", "ий", "ой", "ая", "ое", "ые", "ого", "ему", "ому", "ым", "ими", "ых")
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


    def expand_words_for_bm25(
        self,
        words: List[str]
    ) -> List[str]:
        unique: Set[str] = set()
        ordered: List[str] = []

        for w in words:
            for v in self._generate_word_expansions(w)[: self.max_expansions_per_word]:
                if v not in unique:
                    unique.add(v)
                    ordered.append(v)

        return ordered


    def _generate_word_expansions(
        self,
        word: str
    ) -> List[str]:
        return list(self._expand_word_variants(word))


    def _expand_word_variants(
        self,
        word: str
    ) -> Iterable[str]:
        cleaned = self.whitespace_normalizer.sub(" ", word.strip())
        if not cleaned:
            return
        yield from self._dedup(
            cleaned,
            *self._get_db_synonyms(cleaned),
            *self._case_variants(cleaned),
            *self._hyphen_variants(cleaned),
            *self._year_variants(cleaned),
            *self._translit_variants(cleaned),
            *self._kbd_layout_variants(cleaned),
            *self._morph_variants(cleaned),
            *self._symbol_variants(cleaned),
        )


    def _get_db_synonyms(
        self,
        word: str
    ) -> List[str]:
        return list(self.synonym_database.get(word.lower(), []))


    def _case_variants(
        self,
        text: str
    ) -> List[str]:
        return list({fn(text) for fn in self.case_variants})


    def _hyphen_variants(
        self,
        text: str
    ) -> List[str]:
        parts = [p for p in self.whitespace_normalizer.split(text) if p]
        if len(parts) <= 1:
            return [text]
        out = set()
        for joiner in self.word_joiners:
            out.add(joiner.join(parts))
        return list(out)


    def _year_variants(
        self,
        text: str
    ) -> List[str]:
        m = self.year_pattern.findall(text)
        if not m:
            return []
        out: Set[str] = set()
        for sep in self.punctuation_separators:
            out.add(self.year_pattern.sub(lambda t: f"{sep}{t.group(0)}", text))
            out.add(self.year_pattern.sub(lambda t: f"{t.group(0)}{sep}", text))
        return list(out)


    def _translit_variants(
        self,
        text: str
    ) -> List[str]:
        cyr = self._to_cyrillic(text)
        lat = self._to_latin(text)
        out = {cyr, lat}
        for fn in self.case_variants:
            out.add(fn(cyr)); out.add(fn(lat))
        return list(out)


    def _kbd_layout_variants(
        self,
        text: str
    ) -> List[str]:
        en = "".join(self.keyboard_layout_ru_to_en.get(ch, ch) for ch in text)
        ru = "".join(self.keyboard_layout_en_to_ru.get(ch, ch) for ch in text)
        return list({en, ru})


    def _morph_variants(
        self,
        word: str
    ) -> List[str]:
        stem = re.sub(r"(ий|ый|ой|ая|ое|ые|ого|ему|ому|ыми|ими|ых|ах|ях|ам|ям|ов|ев|ой|ей|у|ю|а|я|ы|и)$", "", word.lower())
        out: Set[str] = set()
        for a in self.adjective_endings: out.add(stem + a)
        for n in self.noun_endings: out.add(stem + n)
        return list(out)


    def _symbol_variants(
        self,
        text: str
    ) -> List[str]:
        s = text.replace("№", "No").replace("no", "No").replace("%", " percent ")
        return list({s, s.replace(" ", ""), s.replace(" ", "-")})


    def _to_latin(
        self,
        text: str
    ) -> str:
        out = []
        for ch in unicodedata.normalize("NFKC", text):
            out.append(self.russian_to_latin_map.get(ch.lower(), ch))
        return "".join(out)


    def _to_cyrillic(
        self,
        text: str
    ) -> str:
        out = []
        i = 0
        while i < len(text):
            two = text[i:i+2].lower()
            one = text[i].lower()
            mapped = None
            for cyr, lat in self.russian_to_latin_map.items():
                if isinstance(lat, str) and len(lat) == 2 and lat == two:
                    mapped = cyr; i += 2; break
            if mapped is None:
                mapped = next((cyr for cyr, lat in self.russian_to_latin_map.items() if lat == one), text[i])
                i += 1
            out.append(mapped)
        return "".join(out)


    def _dedup(self, *vals: str) -> Iterable[str]:
        seen: Set[str] = set()
        for v in vals:
            vv = self.whitespace_normalizer.sub(" ", v).strip()
            if vv and vv not in seen:
                seen.add(vv)
                yield vv


    def _create_russian_to_latin_mapping(self) -> Dict[str, str]:
        return {
            "а": "a","б": "b","в": "v","г": "g","д": "d","е": "e","ё": "e","ж": "zh","з": "z",
            "и": "i","й": "i","к": "k","л": "l","м": "m","н": "n","о": "o","п": "p","р": "r",
            "с": "s","т": "t","у": "u","ф": "f","х": "h","ц": "c","ч": "ch","ш": "sh",
            "щ": "shch","ъ": "","ы": "y","ь": "","э": "e","ю": "yu","я": "ya",
        }


    def _create_keyboard_layout_mappings(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        ru = "ёйцукенгшщзхъфывапролджэячсмитьбю"
        en = "`qwertyuiop[]asdfghjkl;'zxcvbnm,."
        ru2en = {r: e for r, e in zip(ru, en)}
        en2ru = {e: r for r, e in zip(ru, en)}
        ru2en.update({r.upper(): e.upper() for r, e in zip(ru, en)})
        en2ru.update({e.upper(): r.upper() for r, e in zip(ru, en)})
        return ru2en, en2ru


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

            "расписание": [
                "календарь егэ", "даты экзаменов", "сроки проведения", "график", "периоды проведения",
            ],
            "время": [
                "продолжительность", "длительность", "лимит времени", "тайминг", "временной регламент",
            ],
            "регламент": [
                "порядок проведения", "инструкция", "методические рекомендации", "письмо рособрнадзора",
            ],
        }



