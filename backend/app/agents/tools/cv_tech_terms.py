"""Noms d'outils, de langages, de plateformes et de méthodes que le validateur des modifications
de CV (6.12) reconnaît dans un texte (liste écrite dans le code, en minuscules). Elle ne prétend
pas être complète : un outil inconnu est repris par les mots clés et les outils de l'offre, et par
la règle des noms propres du validateur.

Sont écartés exprès les mots de la langue courante (« go », « r », « c », « net », « word »,
« notion », « chef », « express ») : « Golang » remplace « go ». Les termes à signes
(« c++ », « c# », « node.js », « ci/cd ») sont comparés après `normalize_term`."""

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

# Les termes de `TECH_TERMS` qui sont aussi des mots courants du français ou de l'anglais, et
# seulement eux : ils ne comptent comme outil que sous leur forme de produit, un mot capitalisé hors
# début de phrase (« Vue », « REST ») ou suivi d'un qualificatif (« vue.js », « spring boot »,
# « rest api »). Écrits en minuscules, ils sont du langage ordinaire (« vue d'ensemble », « plus
# vite », « tableaux de bord »). Un terme que l'offre nomme reste un terme de l'offre.
# Un outil qui n'a, dans un CV, que sa lecture d'outil (« react », « bash », « excel », « spark »,
# « windows », « slack », « helm », « sap »…) n'entre pas ici : en minuscules, il reste un outil.
# Chaque mot gardé a un sens courant fréquent : vue, vite, spring, rest, swift, hive, consul,
# sketch, unity, unreal, oracle, tableau (« tableau de bord »), soap, vault, rust, transformers
# (le verbe « transformer »), rails.
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
