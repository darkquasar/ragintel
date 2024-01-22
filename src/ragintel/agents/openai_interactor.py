# from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel

from ragintel.databases import opensearchdb
from ragintel.loaders import config_loader
from ragintel.templates import pydantinc_intel_base


class OpenAIInteractor:
    def __init__(
        self,
        api_key: str = None,
        config_file: str = None,
        rag_db: opensearchdb.OpenSearchDB = None,
    ):

        if config_file is not None:
            _config_loader = config_loader.ConfigLoader()
            config = _config_loader.load_config(config_file)

        else:
            try:
                self.OPENAI_API_KEY = api_key
            except ValueError:
                logger.error("Missing API key")
                raise ValueError("Missing API key")

        self.OPENAI_API_KEY = config.llm.config.api_key
        self.llm_model = config.llm.config.model
        self.llm_temperature = config.llm.config.temperature
        self.llm_max_tokens = config.llm.config.max_tokens
        self.llm_top_p = config.llm.config.top_p
        self.llm_stream = config.llm.config.stream
        self.rag_db = rag_db
        self.retriever = self.rag_db.vector_store.as_retriever()

    def format_docs(self, docs):
        return "\n\n".join([d.page_content for d in docs])

    def interact(
        self,
        query: str,
        template_type: str = "simple_text",
        template: str = None,
        output_parser: str = None,
    ) -> str:

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
            template = template

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
                "question": RunnablePassthrough(),
            }
            | prompt
            | model
            | StrOutputParser()
        )

        answer = chain.invoke(query)

        return answer

    def interact_structured(
        self,
        query: str,
        pydantic_template: BaseModel = None,
        prompt_template: str = None,
    ) -> str:

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
        result = chain.invoke(query)

        return result
