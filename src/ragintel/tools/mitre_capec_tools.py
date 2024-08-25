
from box import Box
from langchain.tools import tool
from loguru import logger
from stix2 import FileSystemSource, Filter


class CAPECAttackPatterns:
    def __init__(self, capec_src_folder: str):

        self.src = FileSystemSource(capec_src_folder)
        logger.debug(f"Initialized CAPEC Attack Pattern processor with folder: {capec_src_folder}")

    @tool
    def get_attack_pattern_by_capec_id(self, capec_id):
        """Search for CAPEC Attack Patterns by CAPEC ID"""

        filters = [
            Filter('type', '=', 'attack-pattern'),
            Filter('external_references.external_id', '=', 'CAPEC-' + capec_id),
            Filter('external_references.source_name', '=', 'capec')
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_attack_pattern_by_capec_ref_id(self, capec_ref_id):
        """Search for CAPEC Attack Patterns by CAPEC Reference ID"""

        filters = [
            Filter('type', '=', 'attack-pattern'),
            Filter('id', '=', capec_ref_id)
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_attack_pattern_by_name(self, name):
        """Search for CAPEC Attack Patterns by Name"""

        filters = [
            Filter('type', '=', 'attack-pattern'),
            Filter('name', 'contains', name)
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_attack_pattern_by_description(self, description):
        """Search for CAPEC Attack Patterns by Description"""

        filters = [
            Filter('type', '=', 'attack-pattern'),
            Filter('description', 'contains', description)
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_attack_pattern_id(self, attack_pattern_id):
        """Get CAPEC Attack Pattern ID"""

        filters = [
            Filter('type', '=', 'attack-pattern'),
            Filter('id', '=', attack_pattern_id)
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes[0].id

class CAPECCoursesOfAction:

    def __init__(self, capec_src_folder: str):

        self.src = FileSystemSource(capec_src_folder)
        logger.debug(f"Initialized CAPEC Course of Action processor with folder: {capec_src_folder}")

    @tool
    def get_course_of_action_by_name(self, name):
        """Search for CAPEC Courses of Action by Name"""

        filters = [
            Filter('type', '=', 'course-of-action'),
            Filter('name', 'contains', name)
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_course_of_action_by_id(self, capec_ref_id):
        """Search for CAPEC Courses of Action by ID"""

        filters = [
            Filter('type', '=', 'course-of-action'),
            Filter('id', '=', capec_ref_id),
        ]

        list_of_boxes = [Box(d) for d in self.src.query(filters)]
        logger.debug(f"CAPEC Objects loaded: {len(list_of_boxes)}")

        return list_of_boxes

    @tool
    def get_relationship_by_attack_pattern_id(self, capec_ref_id: list[Box]):
        """Get Courses of Action for CAPEC Attack Patterns"""

        for _capec_ref in capec_ref_id:

            filters = [
                Filter('type', '=', 'relationship'),
                Filter('target_ref', '=', _capec_ref.id),
                Filter('relationship_type', '=', 'mitigates')
            ]

            list_of_boxes = [Box(d) for d in self.src.query(filters)]
            logger.debug(f"Loaded {len(list_of_boxes)} Courses of Action for Attack Pattern with Name {_capec_ref.name} (Ref: {_capec_ref.id})")

            yield list_of_boxes
