import pandas as pd
import torch
import transformers
from loguru import logger
from tqdm import tqdm

from ragintel.utils import config_loader


class MitreTRAMInteractor:
    def __init__(self, api_key: str | None = None, config_file: str | None = None):
        if config_file is not None:
            _config_loader = config_loader.ConfigLoader()
            config = _config_loader.load_config(config_file)

        else:
            try:
                self.OPENAI_API_KEY = api_key
            except ValueError:
                logger.error("Missing API key")
                msg = "Missing API key"
                raise ValueError(msg)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        bert = (
            transformers.BertForSequenceClassification.from_pretrained("scibert_multi_label_model")
            .to(device)
            .eval()
        )
        tokenizer = transformers.BertTokenizer.from_pretrained("allenai/scibert_scivocab_uncased")

        self.CLASSES = (
            "T1003.001",
            "T1005",
            "T1012",
            "T1016",
            "T1021.001",
            "T1027",
            "T1033",
            "T1036.005",
            "T1041",
            "T1047",
            "T1053.005",
            "T1055",
            "T1056.001",
            "T1057",
            "T1059.003",
            "T1068",
            "T1070.004",
            "T1071.001",
            "T1072",
            "T1074.001",
            "T1078",
            "T1082",
            "T1083",
            "T1090",
            "T1095",
            "T1105",
            "T1106",
            "T1110",
            "T1112",
            "T1113",
            "T1140",
            "T1190",
            "T1204.002",
            "T1210",
            "T1218.011",
            "T1219",
            "T1484.001",
            "T1518.001",
            "T1543.003",
            "T1547.001",
            "T1548.002",
            "T1552.001",
            "T1557.001",
            "T1562.001",
            "T1564.001",
            "T1566.001",
            "T1569.002",
            "T1570",
            "T1573.001",
            "T1574.002",
        )

        self.ID_TO_NAME = {
            "T1055": "Process Injection",
            "T1110": "Brute Force",
            "T1055.004": "Asynchronous Procedure Call",
            "T1047": "Windows Management Instrumentation",
            "T1078": "Valid Accounts",
            "T1140": "Deobfuscate/Decode Files or Information",
            "T1016": "System Network Configuration Discovery",
            "T1057": "Process Discovery",
            "T1078.004": "Cloud Accounts",
            "T1518.001": "Security Software Discovery",
            "T1090.001": "Internal Proxy",
            "T1078.001": "Default Accounts",
            "T1071.001": "Web Protocols",
            "T1082": "System Information Discovery",
            "T1110.003": "Password Spraying",
            "T1484.001": "Group Policy Modification",
            "T1106": "Native API",
            "T1027.008": "Stripped Payloads",
            "T1548.002": "Bypass User Account Control",
            "T1105": "Ingress Tool Transfer",
            "T1033": "System Owner/User Discovery",
            "T1569.002": "Service Execution",
            "T1566.001": "Spearphishing Attachment",
            "T1059.003": "Windows Command Shell",
            "T1053.005": "Scheduled Task",
            "T1547.001": "Registry Run Keys / Startup Folder",
            "T1041": "Exfiltration Over C2 Channel",
            "T1210": "Exploitation of Remote Services",
            "T1005": "Data from Local System",
            "T1219": "Remote Access Software",
            "T1552.001": "Credentials In Files",
            "T1068": "Exploitation for Privilege Escalation",
            "T1543.003": "Windows Service",
            "T1570": "Lateral Tool Transfer",
            "T1027": "Obfuscated Files or Information",
            "T1113": "Screen Capture",
            "T1078.003": "Local Accounts",
            "T1012": "Query Registry",
            "T1055.002": "Portable Executable Injection",
            "T1573.001": "Symmetric Cryptography",
            "T1055.001": "Dynamic-link Library Injection",
            "T1072": "Software Deployment Tools",
            "T1027.001": "Binary Padding",
            "T1190": "Exploit Public-Facing Application",
            "T1218.011": "Rundll32",
            "T1090.003": "Multi-hop Proxy",
            "T1055.012": "Process Hollowing",
            "T1056.001": "Keylogging",
            "T1055.008": "Ptrace System Calls",
            "T1204.002": "Malicious File",
            "T1083": "File and Directory Discovery",
            "T1070.004": "File Deletion",
            "T1110.004": "Credential Stuffing",
            "T1036.005": "Match Legitimate Name or Location",
            "T1574.002": "DLL Side-Loading",
            "T1090": "Proxy",
            "T1027.003": "Steganography",
            "T1027.007": "Dynamic API Resolution",
            "T1074.001": "Local Data Staging",
            "T1090.002": "External Proxy",
            "T1564.001": "Hidden Files and Directories",
            "T1021.001": "Remote Desktop Protocol",
            "T1112": "Modify Registry",
            "T1027.005": "Indicator Removal from Tools",
            "T1003.001": "LSASS Memory",
            "T1027.002": "Software Packing",
            "T1090.004": "Domain Fronting",
            "T1562.001": "Disable or Modify Tools",
            "T1027.006": "HTML Smuggling",
            "T1095": "Non-Application Layer Protocol",
            "T1027.009": "Embedded Payloads",
            "T1078.002": "Domain Accounts",
        }

        def create_subsequences(self, document: str, n: int = 13, stride: int = 5) -> list[str]:
            words = document.split()
            return [" ".join(words[i : i + n]) for i in range(0, len(words), stride)]

        def predict_multi_label(
            self, document: str, threshold: float = 0.5, n: int = 13, stride: int = 5
        ):
            text_instances = create_subsequences(document, n, stride)
            tokenized_instances = tokenizer(
                text_instances,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=512,
            ).input_ids

            predictions = []
            batch_size = 10
            slice_starts = tqdm(list(range(0, tokenized_instances.shape[0], batch_size)))

            with torch.no_grad():
                for i in slice_starts:
                    x = tokenized_instances[i : i + batch_size].to(device)
                    out = bert(x, attention_mask=x.ne(tokenizer.pad_token_id).to(int))
                    predictions.extend(out.logits.sigmoid().to("cpu"))

            probabilities = pd.DataFrame(
                torch.vstack(predictions), columns=self.CLASSES, index=text_instances
            )

            result: list[tuple[str, set[str]]] = [
                (text, {self.ID_TO_NAME[k] + " - " + k for k, v in clses.items() if v})
                for text, clses in probabilities.gt(threshold).T.to_dict().items()
            ]

            result_iter = iter(result)
            current_text, current_labels = next(result_iter)
            overlap = n - stride
            out = []

            for text, labels in result_iter:
                if labels != current_labels:
                    out.append((current_text, current_labels))
                    current_text = text
                    current_labels = labels
                    continue

                current_text += " " + " ".join(text.split()[overlap:])

            out_df = pd.DataFrame(out)
            out_df.columns = ["segment", "label(s)"]
            return out_df
