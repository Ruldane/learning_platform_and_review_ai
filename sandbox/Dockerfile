# Bac à sable d'exécution de code (phase 10, 10.A1). Le code de l'utilisateur tourne ici, jamais dans
# le back : pas de réseau, pas de socket, pas de secret (voir docker-compose.yml). Même base figée
# que le back (D30). Construire avec `docker build -t learning_career_platform-sandbox:latest sandbox`.
FROM python:3.12.16-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Seul `pytest` est fourni au code : les exercices en dépendent, aucun autre paquet (pas de réseau
# à l'exécution, donc pas d'installation possible).
RUN pip install --no-cache-dir pytest==9.2.0

# uid 20000 : celui du code utilisateur (sans shell, sans dossier perso). gid 12345 : celui du
# volume d'échange, que le lanceur et le back partagent ; le code n'en fait pas partie.
RUN groupadd --gid 20000 sandbox \
    && useradd --uid 20000 --gid 20000 --no-create-home --shell /usr/sbin/nologin sandbox \
    && groupadd --gid 12345 spool \
    && mkdir -p /spool /work /opt/sandbox \
    && chown root:12345 /spool \
    && chmod 2770 /spool \
    && chmod 0755 /work \
    && (find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true)

COPY runner.py runner_exec.py runner_job.py runner_proc.py /opt/sandbox/
RUN chmod 0644 /opt/sandbox/*.py

WORKDIR /opt/sandbox
CMD ["python", "-u", "/opt/sandbox/runner.py"]
