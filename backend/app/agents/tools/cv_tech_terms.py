"""Names of tools, languages, platforms and methods that the CV change validator
(6.12) recognizes in a text (list written in the code, in lower case). It does not claim
to be complete: an unknown tool is taken up by the offer's keywords and tools, and by
the validator's proper-noun rule.

Common-language words are excluded on purpose ("go", "r", "c", "net", "word",
"notion", "chef", "express"): "Golang" replaces "go". Terms with signs
("c++", "c#", "node.js", "ci/cd") are compared after `normalize_term`."""

TECH_TERMS: frozenset[str] = frozenset(
    """
    python java javascript typescript golang rust kotlin swift scala ruby php perl julia matlab
    c++ c# bash powershell sql nosql graphql html css sass lua dart haskell elixir cobol
    node.js nodejs deno react angular vue svelte next.js nuxt django flask fastapi spring
    laravel symfony rails nestjs
    aws azure gcp ibm-cloud ovh scaleway heroku vercel netlify cloudflare
    docker kubernetes k8s helm openshift terraform ansible puppet pulumi vagrant
    jenkins gitlab github bitbucket git svn circleci travis ci/cd devops gitops mlops
    prometheus grafana kibana elasticsearch opensearch logstash datadog splunk sentry
    linux unix ubuntu debian windows macos nginx apache kafka rabbitmq redis memcached celery
    postgresql postgres mysql mariadb mongodb cassandra dynamodb sqlite oracle snowflake
    bigquery redshift databricks clickhouse neo4j influxdb supabase firebase
    spark hadoop airflow dbt flink hive presto trino tableau powerbi looker metabase
    pandas numpy scipy matplotlib seaborn plotly scikit-learn sklearn tensorflow keras pytorch
    xgboost lightgbm opencv huggingface transformers spacy nltk jupyter mlflow kubeflow
    langchain langgraph llamaindex llm llms rag openai anthropic gpt chatgpt
    llama ollama vllm pinecone qdrant weaviate faiss pgvector embeddings
    nlp mlops fine-tuning rlhf prompt-engineering
    scrum kanban agile itil prince2 jira confluence trello asana slack
    figma sketch photoshop illustrator excel sap salesforce hubspot zendesk servicenow
    odoo workday sharepoint
    rest grpc soap websocket oauth jwt saml openid sso mqtt
    junit pytest selenium cypress playwright jest mocha cucumber postman
    tdd bdd ddd microservices serverless
    android ios flutter react-native xamarin unity unreal
    webpack vite babel eslint prettier npm yarn pnpm maven gradle poetry pip conda
    opentelemetry istio envoy consul vault keycloak
    iso27001 rgpd gdpr soc2 hipaa
    """.split()  # noqa: SIM905
)

# Terms of `TECH_TERMS` that are also common words of French or English, and
# only those: they count as a tool only in their product form, a capitalized word not at the start
# of a sentence ("Vue", "REST") or followed by a qualifier ("vue.js", "spring boot",
# "rest api"). Written in lower case, they are ordinary language ("vue d'ensemble", "plus
# vite", "tableaux de bord"). A term the offer names stays an offer term.
# A tool that, in a CV, only has its tool reading ("react", "bash", "excel", "spark",
# "windows", "slack", "helm", "sap"...) does not enter here: in lower case, it stays a tool.
# Each kept word has a frequent common meaning: vue, vite, spring, rest, swift, hive, consul,
# sketch, unity, unreal, oracle, tableau ("tableau de bord"), soap, vault, rust, transformers
# (the verb "transformer"), rails.
_JS = ("js",)
AMBIGUOUS_TERMS: dict[str, frozenset[str]] = {
    "vue": frozenset({*_JS, "2", "3", "router", "native"}),
    "vite": frozenset(_JS),
    "spring": frozenset({"boot", "framework", "cloud", "mvc", "security", "data", "batch"}),
    "rest": frozenset({"api", "apis", "ful"}),
    "swift": frozenset({"ui", "package"}),
    "hive": frozenset({"ql", "metastore"}),
    "consul": frozenset({"connect"}),
    "sketch": frozenset({"app"}),
    "unity": frozenset({"engine", "3d"}),
    "unreal": frozenset({"engine"}),
    "oracle": frozenset({"db", "database", "cloud", "sql", "apex"}),
    "tableau": frozenset({"software", "desktop", "server", "prep", "public"}),
    "soap": frozenset({"api", "ui"}),
    "vault": frozenset({"server"}),
    "rust": frozenset({"lang"}),
    "transformers": frozenset({"library"}),
    "rails": frozenset({"app", "api"}),
}
