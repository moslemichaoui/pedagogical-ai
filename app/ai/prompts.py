"""Arabic-first prompt templates for pedagogical content generation."""
from typing import List, Dict, Any


SYSTEM_PROMPT = """You are an expert primary-school pedagogical designer specialized in الإيقاظ العلمي (Scientific Awakening) for Arabic-speaking students.

Your role is to generate comprehensive, practical lesson plans in Modern Standard Arabic (العربية الفصحى) that are immediately usable by teachers in the classroom.

IMPORTANT RULES:

1. LANGUAGE: All educational content must be in clear Modern Standard Arabic. Adapt vocabulary to the student's educational level.

2. DURATION: Respect the requested lesson duration. The total duration of all lesson phases must approximately equal the requested duration.

3. OBJECTIVES: Align all content with the teacher's specified learning objectives.

4. SCIENTIFIC ACCURACY: Use scientific terminology accurately. Do not make unsupported scientific claims.

5. PRACTICALITY: Prefer practical classroom activities that can be implemented with common materials.

6. EXPERIMENTS: Include scientific experiments only when they are pedagogically appropriate and safe. Never recommend dangerous materials or unsafe procedures.

7. SOURCE INTEGRITY: Use the retrieved educational context as your primary reference. Never invent information from the provided sources.

8. CITATION HONESTY: If the retrieved sources do not contain the requested information, explicitly state: "هذه المعلومات غير متوفرة في المصادر المقدمة" (This information is not available in the provided sources).

9. REFERENCE INTEGRITY: Do not invent citations or references. Only cite sources that are actually provided in the retrieved context.

10. DISTINCTION: Clearly distinguish between information supported by sources and pedagogical structure you generate.

11. CULTURAL APPROPRIATENESS: Ensure all examples, activities, and content are culturally appropriate for Arabic-speaking primary school students.

12. AGE APPROPRIATENESS: Adapt complexity and language to the specified educational level (السنة الأولى إلى السنة السادسة ابتدائي).

The lesson plan must follow this structured JSON format exactly:
{
  "title": "lesson title in Arabic",
  "subject": "subject in Arabic",
  "educational_level": "educational level in Arabic",
  "duration": total duration in minutes (integer),
  "competency": "target competency in Arabic",
  "learning_objectives": ["objective 1", "objective 2", ...],
  "prerequisites": ["prerequisite 1", "prerequisite 2", ...],
  "materials": ["material 1", "material 2", ...],
  "key_concepts": ["concept 1", "concept 2", ...],
  "introduction": "detailed introduction and situation de départ",
  "lesson_phases": [
    {
      "name": "phase name in Arabic",
      "duration": duration in minutes (integer),
      "teacher_actions": ["action 1", "action 2", ...],
      "learner_actions": ["action 1", "action 2", ...],
      "guiding_questions": ["question 1", "question 2", ...],
      "expected_responses": ["response 1", "response 2", ...],
      "activities": ["activity 1", "activity 2", ...]
    }
  ],
  "teacher_actions": ["general teacher action 1", ...],
  "learner_actions": ["general learner action 1", ...],
  "guiding_questions": ["general guiding question 1", ...],
  "expected_answers": ["expected answer 1", ...],
  "activities": ["classroom activity 1", ...],
  "experiments": ["experiment description 1", ...],
  "exercises": ["exercise 1", ...],
  "assessment": "detailed assessment description",
  "remediation": "support and remediation activities",
  "summary": "lesson summary and synthesis",
  "homework": "homework or follow-up activities",
  "sources": ["source 1", "source 2", ...]
}

Respond with valid JSON only. Do not include any text before or after the JSON response."""


def build_lesson_generation_prompt(
    subject: str,
    educational_level: str,
    topic: str,
    duration: int,
    objectives: List[str],
    difficulty: str,
    language: str,
    retrieved_context: List[Dict[str, Any]],
    teacher_instructions: str = None
) -> str:
    """Build the user prompt for lesson generation."""
    
    # Format retrieved context
    context_text = ""
    if retrieved_context:
        context_text = "\n\nRETRIEVED EDUCATIONAL CONTEXT:\n"
        for i, ctx in enumerate(retrieved_context, 1):
            text = ctx.get('text', '')
            metadata = ctx.get('metadata', {})
            source = metadata.get('filename', 'Unknown source')
            page = metadata.get('page_number')
            
            context_text += f"\n--- Source {i}: {source}"
            if page:
                context_text += f" (Page {page})"
            context_text += " ---\n"
            context_text += text + "\n"
    else:
        context_text = "\n\nRETRIEVED EDUCATIONAL CONTEXT:\nNo relevant context was retrieved from the document database.\n"
    
    # Format objectives
    objectives_text = ""
    if objectives:
        objectives_text = "\n".join(f"- {obj}" for obj in objectives)
    else:
        objectives_text = "No specific objectives provided."
    
    # Format teacher instructions
    instructions_text = ""
    if teacher_instructions:
        instructions_text = f"\n\nTEACHER INSTRUCTIONS:\n{teacher_instructions}"
    
    prompt = f"""Generate a comprehensive lesson plan for the following request:

SUBJECT: {subject}
EDUCATIONAL LEVEL: {educational_level}
TOPIC: {topic}
DURATION: {duration} minutes
DIFFICULTY: {difficulty}
LANGUAGE: {language}

LEARNING OBJECTIVES:
{objectives_text}
{instructions_text}
{context_text}

Please generate a complete, practical lesson plan that:
1. Respects the {duration}-minute duration (total phase durations should equal approximately {duration} minutes)
2. Addresses all specified learning objectives
3. Uses the retrieved educational context as the primary reference
4. Is appropriate for {educational_level} students
5. Includes practical classroom activities
6. Provides clear guidance for the teacher
7. Includes appropriate assessment methods

Return the lesson plan as valid JSON following the exact structure specified in the system prompt."""
    
    return prompt


def build_duration_validation_prompt(
    requested_duration: int,
    generated_phases: List[Dict[str, Any]]
) -> str:
    """Build a prompt to validate and adjust phase durations if needed."""
    
    total_generated = sum(phase.get('duration', 0) for phase in generated_phases)
    
    prompt = f"""The generated lesson plan has a duration mismatch.

REQUESTED DURATION: {requested_duration} minutes
GENERATED TOTAL DURATION: {total_generated} minutes
DIFFERENCE: {abs(requested_duration - total_generated)} minutes

Current phases:
"""
    
    for i, phase in enumerate(generated_phases, 1):
        name = phase.get('name', 'Unknown')
        duration = phase.get('duration', 0)
        prompt += f"{i}. {name}: {duration} minutes\n"
    
    prompt += f"""
Please adjust the phase durations so that the total equals approximately {requested_duration} minutes.
Maintain the relative importance of each phase but scale durations appropriately.
Return the corrected phases as valid JSON with the same structure."""
    
    return prompt


def build_arabic_content_validation_prompt(lesson_plan: Dict[str, Any]) -> str:
    """Build a prompt to validate Arabic content quality."""
    
    prompt = """Validate the Arabic content quality of this lesson plan:

Check for:
1. Proper Modern Standard Arabic (العربية الفصحى)
2. Age-appropriate vocabulary for the educational level
3. Grammatical correctness
4. Cultural appropriateness
5. Scientific terminology accuracy

Lesson plan to validate:
""" + str(lesson_plan) + """

Provide a brief assessment of the Arabic content quality and any specific issues found."""
    
    return prompt
