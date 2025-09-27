from __future__ import annotations

from loguru import logger

from src.adapters.vllm_adapter import VLLMAdapter


class LLMExpansionService:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()


    async def expand_question_for_retriever(
        self,
        normalized_question: str
    ) -> str:
        try:
            system_prompt = """Rewrite the user’s Russian query into one single Russian search-style keyword string (comma-separated short phrases) that preserves the original meaning, goal, entities, constraints, and logical OR relationships (“или”). The result must read like a Google-style search query, not advice.
Output Style
One line, comma-separated keyword phrases (no bullets, no numbering, no quotes, no extra text).
Neutral, concise, retrieval-oriented.
Keep “или” and explicit pairings exactly as in the user’s text.
HARD LOCK: Verbatim Entities (DO NOT ALTER)
Before answering, identify LOCKED_ENTITIES in the input: names/abbreviations of universities, faculties, organizations, exams, brands, acronyms, and any proper names.
You MUST copy each LOCKED entity exactly as it appears in the input (character-for-character): same spelling, casing, hyphens, spaces, abbreviations.
Never normalize, correct, inflect, translate, or substitute locked entities.
Examples of forbidden changes:

“ВШЭ” → “Высшая Школа Экономики” or “HSE” (no)

“МГУ” → “Московский государственный университет” (no)

“мехмат”/“матфак” → other forms/cases (no)

Constraints (must follow all)
No meaning drift. Do not change the goal, targets, time horizon, metrics, or structure.
No new entities. Do not add universities, faculties, exams, resources, dates, or metrics not present in the input.
Preserve OR logic. Keep every “или” exactly and maintain any explicit pairings (e.g., “МГУ мехмат или матфак; ВШЭ мехмат”).

Language: Output must be Russian.

Enrichment (optional, small): You MAY add up to 5 very short, clearly on-topic terms (e.g., section names) only if they are obviously implied and do not alter intent. If unsure—omit.
No advice or steps. No plans, how-tos, or recommendations.

Output Format:

Return exactly one line of Russian keywords separated by commas.
No quotes, no leading/trailing text, no multiple lines.
Sanity Checklist (apply before answering)
All LOCKED_ENTITIES appear verbatim (exact glyphs and casing).
All “или” disjunctions and pairings are preserved.
No new entities/requirements were added.
One line, comma-separated, search-style.

Positive Examples (style only):

Input: «реши уравнение x²−5x+6=0»
Output: решить квадратное уравнение x²−5x+6=0, корни уравнения, дискриминант

Input: «я хочу поступить в МГУ либо в Высшую Школу Экономики на мехмат или матфак соответственно. У меня есть год. что нужно?»
Output: поступление в МГУ на мехмат или матфак, поступление в Высшую Школу Экономики на мехмат, план подготовки за год

Negative Examples (do NOT do)"

Changing “или” to “и”, altering pairings, or adding exams/resources not in input.
Altering spelling/casing/abbreviations of proper names.
Producing multiple lines, quotes, or advice."""

            user_prompt = f"Переформулируй вопрос пользователя для расширенного поиска поиска: {normalized_question}"

            max_tokens = max(175, int(len(normalized_question.split()) * 1.5))
            
            expanded_question = await self.vllm_adapter.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=0.3
            )

            logger.info(f"Question expanded: '{normalized_question}' -> '{expanded_question}'")
            return expanded_question

        except Exception as ex:
            logger.error(f"LLM expansion failed: {ex}")
            return normalized_question


    async def health_check(self) -> bool:
        return await self.vllm_adapter.health_check()
