from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field


class AttackPattern(BaseModel):
    """
    Represents an Attack Pattern observed in a cyber threat intel report, designed to break down complex information into manageable chunks. An Attack pattern is a clustering principle that sits above a MITRE ATT&CK Tactic. Attack Patterns encapsulate a common theme or cluster of behaviours displayed by an attacker. An Attack Pattern thus can cut across MITRE ATT&CK transversally, grouping multiple techniques and subtechniques under the same common theme that acts as the clustering principle.
    """

    name: str = Field(description="A concise name or label for the identified attack pattern.")

    summary: str = Field(
        description="""A detailed summary of the attack pattern, capturing its key characteristics,
        involved tactics, techniques, and overall objectives. This should be as comprehensive
        as needed to provide a clear understanding of the pattern."""
    )

    relevant_sections: list[str] | None = Field(
        description="""List of sections or specific excerpts from the report that are directly
        relevant to this attack pattern. Each section has to represent a summary of what that section says in the actual report. It has to be consise but not extremely short. This helps in quickly locating and reviewing the key information."""
    )


class ThreatIntelReport(BaseModel):
    """
    Represents a cyber threat intelligence report containing attack patterns.
    """

    report_name: str = Field(
        description="Full title of the article if clearly identifiable. Inferred title otherwise."
    )

    attack_patterns: list[AttackPattern] = Field(
        description="List of attack patterns extracted from the report."
    )


class AttackerTool(BaseModel):
    """Represents a tool used by an attacker"""

    name: str = Field(
        description="Name or identifier of the tool. Specific tools, malware, or software leveraged by threat actors. This includes malware, exploit kits, specific software, or any technical resources utilized in the attack. Consider variations in naming or descriptions (e.g., 'Ramsay' and 'Ramsay RAT' could refer to the same tool). Do not include tools not mentioned or implied in the article."
    )

    is_lolbin: bool | None = Field(
        description="Indicates whether the tool is a Living-off-the-Land Binary (LOLBin)"
    )

    language: str | None = Field(
        description="Programming language used to develop the tool (if mentioned)"
    )


class MitreTTP(BaseModel):
    """Represents a MITRE ATT&CK tactic, technique, and subtechnique"""

    tactic: str = Field(
        description="The overarching tactic. Stick strictly to MITRE ATT&CK tactics. Default to 'Unknown' if the tactic is not explicitly mentioned in the article."
    )

    technique: str | None = Field(
        description="The specific technique within the tactic (if applicable). Stick strictly to MITRE ATT&CK techniques. Default to 'Unknown' if the technique is not explicitly mentioned in the article."
    )

    subtechnique: str | None = Field(
        description="The subtechnique (if applicable). Stick strictly to MITRE ATT&CK subtechniques. Default to 'Unknown' if the subtechnique is not explicitly mentioned in the article."
    )

    long_technique_id: str = Field(
        default=None,
        description="The most granular operation (subtechnique, technique, or tactic) including the ID. Example: 'T1071.001 Application Layer Protocol: Web Protocols'",
    )

    short_technique_id: str | None = Field(
        default=None, description="The ID of the most granular operation. Example: 'T1071.001'"
    )


class TechnologyAffected(BaseModel):
    """Represents a technology targeted or impacted by the attack"""

    name: str = Field(
        description="Name of the technology, platform, or system. Default to 'Unknown' if the technology is not explicitly mentioned in the article."
    )

    version: str | None = Field(
        description="Specific version (if mentioned). Default to 'Unknown' if the version is not explicitly mentioned in the article."
    )

    configuration: str | None = Field(
        description="Relevant configuration details (if available). Default to 'Unknown' if the configuration is not explicitly mentioned in the article."
    )


class CVE(BaseModel):
    """Represents a Common Vulnerability and Exposure (CVE)"""

    id: str = Field(
        description="The CVE identifier (e.g., CVE-2023-1234). Do not invent or guess CVEs. Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )

    description: str | None = Field(
        description="Brief description of the vulnerability. Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )

    cvss_score: float | None = Field(
        description="CVSS severity score (if available). Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )


class IOC(BaseModel):
    """Represents an Indicator of Compromise (IOC) associated with a cyber threat actor. Extract ALL IOCs from the article. Do not invent or hallucinate IOCs, stick to what is literally in the information provided."""

    ioc_type: str = Field(
        description="The type of IOC (e.g., 'file_hash', 'url', 'ja4', 'jarm', 'ja3', 'domain', 'ip_address', 'certificate_fingerprint', 'email_address', 'registry_key', 'user_agent')"
    )
    values: "list[str]" = Field(
        description="A list of IOC values (e.g., ['17d9ef11eacdfa6c4c2d22441804daf5', 'www.example.com', '192.168.1.1'])"
    )


class IntelArticleNested(BaseModel):
    """RAGIntel Intel Article Base model"""

    article_name: str = Field(
        description="Full title of the article if clearly identifiable. Inferred title otherwise."
    )

    mitre_ttps: Optional["list[MitreTTP]"] = Field(
        description="MITRE ATT&CK subtechniques that best apply to the article. Do not invent or guess techniques and stick strictly to MITRE ATT&CK techniques and subtechniques."
    )

    short_description: str = Field(
        description="Summary of the article that captures the main issue and provides context around main techniques used by the threat actor. Ensure the summary is accurate and reflects the article's content. Do not add information not present in the original text."
    )

    threat_actors: Optional["list[str]"] = Field(
        description="Names or aliases of threat actors involved (if mentioned). Include both individual names and group aliases. If the article mentions affiliations or connections to known groups, include those as well. Do not invent or hallucinate threat actor names."
    )

    attacker_tools: Optional["list[AttackerTool]"] = Field(
        description="Specific tools, malware, or software leveraged by threat actors."
    )

    technologies_affected: Optional["list[TechnologyAffected]"] = Field(
        description="Technologies, platforms, or systems targeted or impacted by the attack."
    )

    cves: Optional["list[CVE]"] = Field(
        description="Explicitly mentioned Common Vulnerabilities and Exposures (CVEs). Only include CVEs that are directly stated in the text. Do not invent or guess CVEs."
    )

    ioc: Optional["list[IOC]"] = Field(
        description="Explicitly mentioned Indicators of Compromise like file hashes, URLs, domains, fingerprints, etc. Do not invent or guess IOCs, stick to what is literally in the information provided."
    )

    implied_vulnerabilities: Optional["list[str]"] = Field(
        description="Vulnerabilities inferred from the context, even if not explicitly stated as CVEs. Look for descriptions of exploited weaknesses, security gaps, or unpatched systems. Phrases like 'security flaw', 'exploitable vulnerability', or descriptions of attack impact can be indicative. Exercise extreme caution. Only include if there's very high confidence based on strong evidence in the article. Avoid speculation or vague inferences. Do not invent or hallucinate vulnerabilities."
    )


class IntelArticleFlattened(BaseModel):
    """RAGIntel Intel Article Base model (Flattened)"""

    report_name: str = Field(
        description="Full title of the article if clearly identifiable. Inferred title otherwise."
    )

    # MitreTTP fields
    mitre_ttps_tactic: list[str] | None = Field(
        description="The overarching tactic. Stick strictly to MITRE ATT&CK tactics. Default to 'Unknown' if the tactic is not explicitly mentioned in the article."
    )
    mitre_ttps_technique: list[str] | None = Field(
        description="The specific technique within the tactic (if applicable). Stick strictly to MITRE ATT&CK techniques. Default to 'Unknown' if the technique is not explicitly mentioned in the article."
    )
    mitre_ttps_subtechnique: list[str] | None = Field(
        description="The subtechnique (if applicable). Stick strictly to MITRE ATT&CK subtechniques. Default to 'Unknown' if the subtechnique is not explicitly mentioned in the article."
    )
    mitre_ttps_long_technique_id: list[str] | None = Field(
        description="The most granular operation (subtechnique, technique, or tactic) including the ID. Example: 'T1071.001 Application Layer Protocol: Web Protocols'"
    )
    mitre_ttps_short_technique_id: list[str] | None = Field(
        description="The ID of the most granular operation. Example: 'T1071.001'"
    )

    short_description: str = Field(
        description="Summary of the article that captures the main issue and provides context around main techniques used by the threat actor. Ensure the summary is accurate and reflects the article's content. Do not add information not present in the original text."
    )

    threat_actors: list[str] | None = Field(
        description="Names or aliases of threat actors involved (if mentioned). Include both individual names and group aliases. If the article mentions affiliations or connections to known groups, include those as well. Do not invent or hallucinate threat actor names."
    )

    # AttackerTool fields
    attacker_tools_name: list[str] | None = Field(
        description="Name or identifier of the tool. Specific tools, malware, or software leveraged by threat actors. This includes malware, exploit kits, specific software, or any technical resources utilized in the attack. Consider variations in naming or descriptions (e.g., 'Ramsay' and 'Ramsay RAT' could refer to the same tool). Do not include tools not mentioned or implied in the article."
    )
    attacker_tools_is_lolbin: list[bool] | None = Field(
        description="Indicates whether the tool is a Living-off-the-Land Binary (LOLBin)"
    )
    attacker_tools_language: list[str] | None = Field(
        description="Programming language used to develop the tool (if mentioned)"
    )

    # TechnologyAffected fields
    technologies_affected_name: list[str] | None = Field(
        description="Name of the technology, platform, or system. Default to 'Unknown' if the technology is not explicitly mentioned in the article."
    )
    technologies_affected_version: list[str] | None = Field(
        description="Specific version (if mentioned). Default to 'Unknown' if the version is not explicitly mentioned in the article."
    )
    technologies_affected_configuration: list[str] | None = Field(
        description="Relevant configuration details (if available). Default to 'Unknown' if the configuration is not explicitly mentioned in the article."
    )

    # CVE fields
    cves_id: list[str] | None = Field(
        description="The CVE identifier (e.g., CVE-2023-1234). Do not invent or guess CVEs. Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )
    cves_description: list[str] | None = Field(
        description="Brief description of the vulnerability. Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )
    cves_cvss_score: list[float] | None = Field(
        description="CVSS severity score (if available). Default to 'Unknown' if the CVE is not explicitly mentioned in the article."
    )

    # IOC fields
    ioc_ioc_type: list[str] | None = Field(
        description="The type of IOC (e.g., 'file_hash', 'url', 'domain', 'ip_address', 'certificate_fingerprint', 'email_address', 'registry_key', 'user_agent')"
    )
    ioc_values: list[list[str]] | None = Field(
        description="A list of IOC values (e.g., ['1a2b3c...', 'www.example.com', '192.168.1.1'])"
    )

    implied_vulnerabilities: list[str] | None = Field(
        description="Vulnerabilities inferred from the context, even if not explicitly stated as CVEs. Look for descriptions of exploited weaknesses, security gaps, or unpatched systems. Phrases like 'security flaw', 'exploitable vulnerability', or descriptions of attack impact can be indicative. Exercise extreme caution. Only include if there's very high confidence based on strong evidence in the article. Avoid speculation or vague inferences. Do not invent or hallucinate vulnerabilities."
    )
