"""
AGENT: OpenAI Threat Summarizer
SUMMARY: >
  This interactor will summarize a threat report and provide MITRE ATTCK Tags
  based on OpenAI best guess. The OpenAIInteractor class provides an interface
  for interacting with the OpenAI language model. It allows users to generate
  responses to queries using the RAG (Retrieval-Augmented Generation) approach.
  It provides methods for interacting with the language model, both for plain
  text responses and structured JSON responses.
OUTPUT SCHEMA:
  RAG_Intel_MITRE_Summary:
    properties:
      article_name:
        type: str
        description: Full title of the article
      mitre_ttps:
        type: list
        items:
          type: str
        description: >
          MITRE ATT&CK subtechniques that best apply to the article
      short_description:
        type: str
        description: >
          Summary of the article that captures the main issue and provides
          context around main techniques used by the threat actor

EXAMPLE: |
    interactor = OpenAIInteractor(api_key="YOUR_API_KEY", config_file="config.yaml")
    response = interactor.interact("What is the capital of France?")
    print(response)

    structured_response = interactor.interact_structured("What is the capital of France?")
    print(structured_response)
"""

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel

from ragintel.templates import pydantinc_intel_base
from ragintel.tools import opensearchdb_tools
from ragintel.utils import config_loader


class OpenAIInteractor:
    def __init__(
        self,
        api_key: str | None = None,
        config_file: str | None = None,
        rag_db: opensearchdb_tools.OpenSearchDB = None,
    ):
        """
        Initialize the OpenAIInteractor.

        Args:
            api_key (str): The API key for the OpenAI language model.
            config_file (str): The path to the configuration file.
            rag_db (opensearchdb.OpenSearchDB): An instance of OpenSearchDB for retrieving documents.

        Raises:
            ValueError: If the API key is missing.
        """
        # Load configuration from file if provided
        if config_file is not None:
            _config_loader = config_loader.ConfigLoader()
            config = _config_loader.load_config(config_file)
        else:
            try:
                self.OPENAI_API_KEY = api_key
            except ValueError:
                logger.error("Missing API key")

        # Set configuration values
        self.OPENAI_API_KEY = config.llm.config.api_key
        self.llm_model = config.llm.config.model
        self.llm_temperature = config.llm.config.temperature
        self.llm_max_tokens = config.llm.config.max_tokens
        self.llm_top_p = config.llm.config.top_p
        self.llm_stream = config.llm.config.stream
        self.rag_db = rag_db
        self.retriever = self.rag_db.vector_store.as_retriever()

    def format_docs(self, docs):
        """
        Format the retrieved documents.

        Args:
            docs: The retrieved documents.

        Returns:
            str: The formatted documents.
        """
        return "\n\n".join([d.page_content for d in docs])

    def interact(
        self, query: str, template_type: str = "simple_text", template: str | None = None
    ) -> str:
        """
        Interact with the language model and generate a plain text response.

        Args:
            query (str): The query to generate a response for.
            template_type (str): The type of template to use for the response.
            template (str): The custom template to use for the response.

        Returns:
            str: The generated response.
        """
        # RAG prompt
        if template is None:
            if template_type == "simple_text":
                logger.info(
                    "Using default template: simple_text. Answers will be provided as plain text."
                )
                template = """
                Use the following pieces of context to answer the query at the end.
                If you don't know the answer, just say that you don't know, don't try to make up an answer.

                {context}

                Query: {query}

                Helpful answer:
                """
            elif template_type == "prompt_json":
                logger.info(
                    "Using default template: prompt_json. Answers will be provided as JSON formatted text, to the best of the AI model's capabilities"
                )
                template = """
                Use the following pieces of context to answer the query at the end.
                If you don't know the answer, just say that you don't know, don't try to make up an answer.
                Return structured JSON in your responses:

                {context}

                Wuery: {query}

                JSON formatted helpful answer:
                """
        else:
            logger.info("Using custom template")

        prompt = ChatPromptTemplate.from_template(template)
        logger.info("Loaded Prompte Template")

        # RAG
        model = ChatOpenAI(
            openai_api_key=self.OPENAI_API_KEY,
            model=self.llm_model,
            temperature=self.llm_temperature,
            max_tokens=self.llm_max_tokens,
            top_p=self.llm_top_p,
            stream=self.llm_stream,
        )

        chain = (
            {
                "context": self.retriever | self.format_docs,
                "query": RunnablePassthrough(),
            }
            | prompt
            | model
            | StrOutputParser()
        )

        return chain.invoke(query)

    def interact_structured(
        self,
        query: str,
        pydantic_template: BaseModel = None,
        prompt_template: str | None = None,
    ) -> str:
        """
        Interact with the language model and generate a structured JSON response.

        Args:
            query (str): The query to generate a response for.
            pydantic_template (BaseModel): The Pydantic template for parsing the response.
            prompt_template (str): The custom prompt template to use for the response.

        Returns:
            str: The generated response.
        """
        # 01. Build Pydantic Parser from Pydantic Class
        if pydantic_template is None:
            logger.info("Using default template: RagIntelMITRE")
            pyd_template = pydantinc_intel_base.RagIntelMITRE
            parser = PydanticOutputParser(pydantic_object=pyd_template)
        else:
            logger.info("Using custom template")
            parser = PydanticOutputParser(pydantic_object=pydantic_template)

        # 02. Build RAG Prompt from Template
        if prompt_template is None:
            logger.info("Using prompt template: default.")
            template = """
            Use the following pieces of context to answer the query at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.

            {context}

            Query: {query}

            These are the format intructions: {format_instructions}
            """
        else:
            logger.info("Using custom prompt template")
            template = prompt_template

        # 03. Build Prompt for Chain using Pydantic Parser and Prompt Template
        prompt = ChatPromptTemplate(
            messages=[HumanMessagePromptTemplate.from_template(template)],
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # 04. Obtain handle to llm model
        llm = ChatOpenAI(
            openai_api_key=self.OPENAI_API_KEY,
            model=self.llm_model,
            temperature=self.llm_temperature,
            max_tokens=self.llm_max_tokens,
            top_p=self.llm_top_p,
            stream=self.llm_stream,
        )

        # 05. Build Chain
        chain = (
            {
                "context": self.retriever | self.format_docs,
                "query": RunnablePassthrough(),
            }
            | prompt
            | llm
            | parser
        )

        # Invoke Chain
        return chain.invoke(query)
