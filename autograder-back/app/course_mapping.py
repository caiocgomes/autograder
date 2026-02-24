"""
Mapping between Hotmart bundles and individual courses.

Bundles are combo products that grant access to multiple courses.
When looking up recipients for a course, we need to include buyers
of any bundle that contains that course.

This is defined in code (not DB) so it deploys with the application.
"""

# Bundle hotmart_product_id -> list of course hotmart_product_ids it contains
BUNDLES = {
    "6626505": ["4141338", "6207530", "6624021"],  # A Base de Tudo -> LLMs, CDO, Como Estudar
}

# Individual courses (non-bundle products)
COURSES = {
    "4141338": "O Senhor das LLMs",
    "6207530": "De analista a CDO",
    "7143204": "Do Zero à Analista",
    "6624021": "Como Estudar",
}


def get_source_product_ids(course_hotmart_id: str) -> list[str]:
    """
    Given a course's hotmart_product_id, return all hotmart_product_ids
    whose buyers have access to this course (direct purchase + bundles).
    """
    sources = [course_hotmart_id]
    for bundle_id, course_ids in BUNDLES.items():
        if course_hotmart_id in course_ids:
            sources.append(bundle_id)
    return sources
