from loguru import logger


class IntelReportParserPrompts:
    def __init__(self):
        self.base_prompt = "Produce a clean and valid JSON parsed cyber threat intelligence report based on three pieces of information provided: the threat report itself, the schema definition and a sample complete schema. The output needs to be clean of invalid JSON strings. Avoid invalid JSON. Do not repeat content. Extract ALL IOC if there are any in the report.\n\n# THREAT REPORT:\n{threat_report}\n\n# SCHEMA DEFINITION:\n{schema_definition}\n\n# SAMPLE SCHEMA:\n{sample_schema}"

        self.sample_intel_report_flat = """
        {
            "article_name": "Dragonfly Group Targets Energy Sector with New 'Axle' Malware",
            "mitre_ttps_tactic": [
            "Resource Development",
            "Command and Control",
            "Execution"
            ],
            "mitre_ttps_technique": [
            "Acquire Infrastructure",
            "Application Layer Protocol",
            "Command and Scripting Interpreter"
            ],
            "mitre_ttps_subtechnique": [
            "Compromise Infrastructure",
            "Web Protocols",
            "PowerShell"
            ],
            "mitre_ttps_long_technique_id": [
            "T1583.001 Acquire Infrastructure: Compromise Infrastructure",
            "T1071.001 Application Layer Protocol: Web Protocols",
            "T1059.001 Command and Scripting Interpreter: PowerShell"
            ],
            "mitre_ttps_short_technique_id": [
            "T1583.001",
            "T1071.001",
            "T1059.001"
            ],
            "short_description": "The Dragonfly APT group, known for targeting energy infrastructure, has been observed deploying a new malware strain dubbed 'Axle' in a recent campaign against European energy companies. The malware leverages compromised ICS devices and PowerShell for command and control.",
            "threat_actors": [
            "Dragonfly",
            "Energetic Bear",
            "Crouching Yeti"
            ],
            "attacker_tools_name": [
            "Axle",
            "PowerShell"
            ],
            "attacker_tools_is_lolbin": [
            false,
            true
            ],
            "attacker_tools_language": [
            "C++",
            null
            ],
            "technologies_affected_name": [
            "Siemens SIMATIC S7",
            "Windows Server"
            ],
            "technologies_affected_version": [
            "Unknown",
            "2012 R2"
            ],
            "technologies_affected_configuration": [
            "Unknown",
            "Unknown"
            ],
            "cves_id": [
            "CVE-2022-1234"
            ],
            "cves_description": [
            "Vulnerability in Siemens SIMATIC S7 allowing remote code execution"
            ],
            "cves_cvss_score": [
            9.8
            ],
            "ioc_ioc_type": [
            "file_hash",
            "domain",
            "ip_address"
            ],
            "ioc_values": [
            [
                "17d9ef11eacdfa6c4c2d22441804daf5",
                "9876543210fedcba17d9ef11eacdfa6c"
            ],
            [
                "maliciousdomain.com",
                "anotherbaddomain.net"
            ],
            [
                "192.168.1.100",
                "203.0.113.50"
            ]
            ],
            "implied_vulnerabilities": [
            "Potential zero-day vulnerability exploited in Windows Server 2012 R2"
            ]
        }
        """

        self.sample_intel_report_nested = """
        {
            "article_name": "Dragonfly Group Targets Energy Sector with New 'Axle' Malware",
            "mitre_ttps": [
                {
                    "tactic": "Resource Development",
                    "technique": "Acquire Infrastructure",
                    "subtechnique": "Compromise Infrastructure",
                    "granular_operation": "T1583.001 Acquire Infrastructure: Compromise Infrastructure",
                    "operation_id": "T1583.001"
                },
                {
                    "tactic": "Command and Control",
                    "technique": "Application Layer Protocol",
                    "subtechnique": "Web Protocols",
                    "granular_operation": "T1071.001 Application Layer Protocol: Web Protocols",
                    "operation_id": "T1071.001"
                },
                {
                    "tactic": "Execution",
                    "technique": "Command and Scripting Interpreter",
                    "subtechnique": "PowerShell",
                    "granular_operation": "T1059.001 Command and Scripting Interpreter: PowerShell",
                    "operation_id": "T1059.001"
                }
            ],
            "short_description": "The Dragonfly APT group, known for targeting energy infrastructure, has been observed deploying a new malware strain dubbed 'Axle' in a recent campaign against European energy companies. The malware leverages compromised ICS devices and PowerShell for command and control.",
            "threat_actors": [
                "Dragonfly",
                "Energetic Bear",
                "Crouching Yeti"
            ],
            "attacker_tools": [
                {
                    "name": "Axle",
                    "is_lolbin": false,
                    "language": "C++"
                },
                {
                    "name": "PowerShell",
                    "is_lolbin": true,
                    "language": null
                }
            ],
            "technologies_affected": [
                {
                    "name": "Siemens SIMATIC S7",
                    "version": "Unknown",
                    "configuration": "Unknown"
                },
                {
                    "name": "Windows Server",
                    "version": "2012 R2",
                    "configuration": "Unknown"
                }
            ],
            "cves": [
                {
                    "id": "CVE-2022-1234",
                    "description": "Vulnerability in Siemens SIMATIC S7 allowing remote code execution",
                    "cvss_score": 9.8
                }
            ],
            "implied_vulnerabilities": [
                "Potential zero-day vulnerability exploited in Windows Server 2012 R2"
            ],
            "iocs": [
                {
                    "ioc_type": "file_hash",
                    "values": [
                        "17d9ef11eacdfa6c4c2d22441804daf5",
                        "9876543210fedcba12345f11aab3fa6c"
                    ]
                },
                {
                    "ioc_type": "domain",
                    "values": [
                        "maliciousdomain.com",
                        "anotherbaddomain.net"
                    ]
                },
                {
                    "ioc_type": "ip_address",
                    "values": [
                        "192.168.1.100",
                        "203.0.113.50"
                    ]
                }
            ]
        }
        """

        self.sample_intel_report_nested_attack_patterns_only = """
        {
            "report_name": "Cyber Espionage Campaign Targeting Financial Institutions",
            "attack_patterns": [
            {
                "name": "Credential Harvesting and Lateral Movement",
                "summary": "This attack pattern involves the initial compromise through phishing emails delivering malware capable of stealing credentials. The attackers then leverage these stolen credentials to move laterally within the network, escalating privileges and gaining access to sensitive financial data.",
                "relevant_sections": [
                "Section 3.2: Initial Compromise - Details the phishing campaign and malware analysis.",
                "Section 4.1: Lateral Movement - Describes the techniques used to move within the network and escalate privileges."
                ]
            },
            {
                "name": "Data Exfiltration and Obfuscation",
                "summary": "After gaining access to sensitive data, the attackers employ various techniques to exfiltrate it from the compromised network. This includes data obfuscation methods to evade detection by security tools and personnel.",
                "relevant_sections": [
                "Section 4.3: Data Exfiltration - Outlines the methods used to transfer data out of the network.",
                "Section 4.4: Obfuscation Techniques - Describes the techniques used to hide the exfiltrated data."
                ]
            }
            ]
        }
        """
