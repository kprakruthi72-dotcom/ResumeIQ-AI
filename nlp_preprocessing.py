def extract_skills_from_text(text, skills):
    found = []
    for skill in skills:
        if skill in text:
            found.append(skill)
    return found
