from __future__ import annotations

from loguru import logger

from src.adapters.vllm_adapter import VLLMAdapter


class LLMSplittingService:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()


    async def split_into_expanded_question_semantic_parts(self, expanded_question: str) -> list[str]:
        try:
            system_prompt = """Ты — эксперт по семантическому разбиению пользовательских запросов для последующего ретрива.
Твоя задача — разложить расширенный запрос на непересекающиеся смысловые части (подзапросы), пригодные для поиска контента.

Жёсткие правила

Не искажать цель пользователя. Никаких новых целей, советов, мнений, предупреждений.

Не дробить действия на микрошаги. Одна часть ≠ пошаговая инструкция; это самостоятельный аспект запроса.

Сохранять ключевые ограничения из запроса (вуз/организация, предмет/домен, язык, срок/дата, целевые метрики).

Без дублирования и пересечений. Каждая часть покрывает уникальный аспект; не повторяй одно и то же разными словами.

Количество частей: от 1 до 5. Если запрос по сути один аспект → верни одну часть.

Длина части: минимум 3 слова, максимум 14 слов.

Язык: русский.

Формат вывода — строго: список через ;, каждая часть в кавычках. Никакого текста до/после списка.

Что считать «семантической частью»

Разные аспекты информации внутри одной цели: требования/критерии, план/расписание, ресурсы/методы, контроль/метрики, риски/ограничения, специфика домена.

Если аспектов мало — не выдумывать искусственные части.

Анти-примеры (так делать нельзя):

Делить одну мысль на пошаговые глаголы: «определить цель»; «составить план»; «выполнить план».

Подменять цель пользователя («выбрать другой вуз», «сдать на 70 баллов») — если этого нет в запросе.

Размножать синонимы того же аспекта.

Примеры

Вход: «решить квадратное уравнение x²-5x+6=0, найти корни уравнения, дискриминант»
Выход: "рассчитать дискриминант уравнения x²−5x+6=0"; "получить корни уравнения из дискриминанта"; "проверить корректность корней подстановкой"

Вход: «найти площадь треугольника по заданным параметрам, формула, геометрия»
Выход: "выбрать подходящую формулу площади по заданным параметрам"; "вычислить площадь треугольника по выбранной формуле"

Вход: «как оформить ИП в РФ для онлайн-курсов в 2025 году?»
Выход: "текущие требования к регистрации ИП в РФ в 2025 году"; "налоговые режимы для онлайн-образования и критерии выбора"; "перечень документов и сроки подачи для регистрации ИП"

Отвечай ТОЛЬКО списком подзадач в указанном формате."""

            user_prompt = f"Разбей на семантические части вопрос пользователя: {expanded_question}"

            max_tokens = int(len(expanded_question.split()) * 1.5)
            
            response_text = await self.vllm_adapter.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=0.2
            )

            expanded_question_semantic_parts = self._parse_expanded_question_semantic_parts(response_text)

            logger.info(f"Expanded question split into {len(expanded_question_semantic_parts)} parts: {expanded_question_semantic_parts}")
            return expanded_question_semantic_parts

        except Exception as ex:
            logger.error(f"LLM splitting failed: {ex}")
            return [expanded_question]


    def _parse_expanded_question_semantic_parts(
        self,
        response: str
    ) -> list[str]:
        try:
            cleaned = response.replace('"', '').replace("'", "").strip()
            parts = [part.strip() for part in cleaned.split(';') if part.strip()]

            filtered_parts = [part for part in parts if len(part.split()) >= 3]

            if not filtered_parts:
                return [response.strip()]

            return filtered_parts

        except Exception as ex:
            logger.error(f"Failed to parse semantic parts from response: {ex}")
            return [response.strip()]


    async def health_check(self) -> bool:
        return await self.vllm_adapter.health_check()
