# =============================================================================
# ProLeap COBOL Service - Multi-stage Docker build
# License: AGPL v3 (this container only; HTTP boundary isolates the license)
# =============================================================================

# Stage 1: Build proleap-cobol from source (AGPL modules not on Maven Central)
FROM maven:3.9-eclipse-temurin-17 AS proleap-builder

RUN git clone --depth 1 https://github.com/uwol/proleap-cobol-parser.git /proleap-parser
WORKDIR /proleap-parser
RUN mvn clean install -DskipTests -q

RUN git clone --depth 1 https://github.com/uwol/proleap-cobol.git /proleap-cobol
WORKDIR /proleap-cobol
RUN mvn clean install -DskipTests -q

# Stage 2: Build the service
FROM maven:3.9-eclipse-temurin-17 AS builder

# Copy local Maven repo with proleap artifacts from stage 1
COPY --from=proleap-builder /root/.m2/repository/io/github/uwol /root/.m2/repository/io/github/uwol
COPY --from=proleap-builder /root/.m2/repository/io/proleap /root/.m2/repository/io/proleap

WORKDIR /app
COPY pom.xml .
COPY src/ ./src/
RUN mvn package -DskipTests -q -U

# Stage 3: Minimal runtime image (jammy supports both amd64 and arm64)
FROM eclipse-temurin:17-jre-jammy

RUN groupadd -r proleap && useradd -r -g proleap proleap
WORKDIR /app

COPY --from=builder /app/target/proleap-service-*.jar /app/service.jar
RUN chown -R proleap:proleap /app

USER proleap

EXPOSE 4567

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
  CMD curl -sf http://localhost:4567/v1/cobol/health || exit 1

ENTRYPOINT ["java", "-Xmx512m", "-jar", "/app/service.jar"]
