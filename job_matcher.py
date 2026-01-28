from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class JobMatcher:
    def __init__(self, skills):
        self.skills = skills
        self.vectorizer = TfidfVectorizer()

    def fit(self, job_descriptions, job_meta):
        self.job_meta = job_meta
        self.job_vectors = self.vectorizer.fit_transform(job_descriptions)

    def match(self, resume_text):
        resume_vec = self.vectorizer.transform([resume_text])
        scores = cosine_similarity(resume_vec, self.job_vectors)[0]

        results = []
        for i, score in enumerate(scores):
            results.append({
                "job": self.job_meta[i]["title"],
                "score": round(score * 100, 2),
                "ats": round(score * 100, 2)
            })
        return results
