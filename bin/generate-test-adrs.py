#!/usr/bin/env python3
"""Generate test ADR files for stress testing the visualization."""

import argparse
import random
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DECISIONS_DIR = PROJECT_DIR / "decisions"

TAGS = [
    "frontend", "backend", "infrastructure", "database", "security",
    "api", "testing", "ci-cd", "monitoring", "architecture",
    "performance", "auth", "deployment", "caching", "messaging",
    "observability", "networking", "storage", "ml-ops", "data-pipeline",
    "compliance", "accessibility", "mobile", "ux", "devtools",
]

PROJECTS = [
    "sempl-core", "sempl-core/ui", "sempl-core/agents", "frontier-brain",
    "autobot", "autobot/ontology-generation", "aero-autobot", "oasis",
]

STATUSES = ["accepted"] * 20 + ["proposed"] * 5 + ["superseded"] * 2 + ["deprecated"] * 1

TITLES = [
    "Use {tech} for {domain}",
    "Adopt {tech} over {alt}",
    "Migrate {domain} to {tech}",
    "{tech} as default {domain} strategy",
    "Replace {alt} with {tech} in {domain}",
    "Standardize on {tech} for {domain}",
    "{domain} powered by {tech}",
    "Evaluate {tech} for {domain} workloads",
]

TECHS = [
    "PostgreSQL", "Redis", "Kafka", "gRPC", "GraphQL", "REST", "WebSocket",
    "Terraform", "Pulumi", "Docker", "Kubernetes", "Istio", "Envoy",
    "React", "Vue", "Svelte", "Tailwind", "MUI", "Storybook",
    "PyTorch", "TensorFlow", "ONNX", "Triton", "vLLM",
    "Prometheus", "Grafana", "OpenTelemetry", "Jaeger", "Loki",
    "ArgoCD", "Flux", "Jenkins", "GitHub Actions", "GitLab CI",
    "DynamoDB", "CockroachDB", "ClickHouse", "TimescaleDB", "SQLite",
    "OAuth2", "OIDC", "mTLS", "SPIFFE", "Vault",
    "S3", "MinIO", "Ceph", "GlusterFS", "EFS",
    "RabbitMQ", "NATS", "Pulsar", "SQS", "EventBridge",
    "Playwright", "Cypress", "Vitest", "pytest", "k6",
]

ALTS = ["legacy system", "manual process", "custom solution", "vendor lock-in", "monolith"]

DOMAINS = [
    "authentication", "authorization", "data ingestion", "log aggregation",
    "service mesh", "state management", "build pipeline", "secret management",
    "feature flags", "A/B testing", "error tracking", "rate limiting",
    "load balancing", "auto-scaling", "database migration", "schema validation",
    "API gateway", "event sourcing", "CQRS", "blob storage",
    "search indexing", "caching layer", "session management", "audit logging",
    "alerting", "capacity planning", "chaos engineering", "blue-green deploys",
]

BODY_TEMPLATES = [
    "## Context\n\nTeam needed a reliable {domain} solution. Existing approach "
    "had scaling issues beyond {n} requests/sec.\n\n## Decision\n\n"
    "Adopted {tech}. Key factors: community support, operational maturity, "
    "integration with existing stack.\n\n## Consequences\n\n"
    "- Reduces {domain} latency by ~{pct}%\n- Requires team training\n"
    "- Migration estimated at {weeks} weeks\n\n## Notes\n\nRevisit in Q{q} {year}.",

    "## Context\n\nCurrent {domain} implementation doesn't meet {req} requirements. "
    "Evaluated {n_opts} alternatives.\n\n## Decision\n\n"
    "Selected {tech} based on benchmark results and team expertise.\n\n"
    "## Consequences\n\n- Improved {metric} by {pct}%\n"
    "- Adds operational complexity\n- Need monitoring dashboards\n\n"
    "## Notes\n\nPOC validated in sprint {sprint}.",

    "## Context\n\nAs system grows past {n} services, {domain} becomes critical. "
    "Manual approaches no longer viable.\n\n## Decision\n\n"
    "Standardize on {tech}. All new services must adopt by Q{q}.\n\n"
    "## Consequences\n\n- Consistent {domain} across platform\n"
    "- Short-term migration cost\n- Long-term maintenance reduction\n\n"
    "## Notes\n\nADR may be superseded if requirements change.",
]


def generate_title():
    tmpl = random.choice(TITLES)
    return tmpl.format(
        tech=random.choice(TECHS),
        alt=random.choice(ALTS),
        domain=random.choice(DOMAINS),
    )


def generate_body(title):
    tmpl = random.choice(BODY_TEMPLATES)
    tech = random.choice(TECHS)
    domain = random.choice(DOMAINS)
    return tmpl.format(
        tech=tech, domain=domain, alt=random.choice(ALTS),
        n=random.randint(50, 5000), pct=random.randint(15, 80),
        weeks=random.randint(1, 8), q=random.randint(1, 4),
        year=random.choice(["2026", "2027"]),
        req=random.choice(["scalability", "compliance", "performance", "reliability"]),
        n_opts=random.randint(3, 7), metric=random.choice(["throughput", "latency", "availability"]),
        sprint=random.randint(1, 30), n_services=random.randint(10, 100),
    )


def generate_adr(num, existing_ids):
    adr_id = f"ADR-{num:03d}"
    title = generate_title()
    status = random.choice(STATUSES)
    tags = random.sample(TAGS, k=random.randint(1, 4))
    project = random.choice(PROJECTS)
    date = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

    related = []
    if existing_ids and random.random() < 0.6:
        related = random.sample(existing_ids, k=min(random.randint(1, 3), len(existing_ids)))

    supersedes = []
    if status == "superseded" and existing_ids:
        supersedes = random.sample(existing_ids, k=1)

    body = generate_body(title)

    lines = ["---"]
    lines.append(f"id: {adr_id}")
    lines.append(f"title: \"{title}\"")
    lines.append(f"status: {status}")
    lines.append(f"date: {date}")
    lines.append(f"tags: [{', '.join(tags)}]")
    if supersedes:
        lines.append(f"supersedes: [{', '.join(supersedes)}]")
    else:
        lines.append("supersedes: []")
    if related:
        lines.append(f"related: [{', '.join(related)}]")
    else:
        lines.append("related: []")
    lines.append(f"project: {project}")
    lines.append("---")
    lines.append("")
    lines.append(body)

    slug = title.lower()
    for ch in '"/\\:*?<>|':
        slug = slug.replace(ch, '')
    slug = slug.replace(' ', '-')[:60].rstrip('-')
    filename = f"{adr_id}-{slug}.md"

    return filename, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate test ADR files")
    parser.add_argument("--count", type=int, default=1000, help="Number of ADRs to generate")
    parser.add_argument("--start", type=int, default=None, help="Starting ADR number (auto-detects if omitted)")
    parser.add_argument("--clean", action="store_true", help="Remove generated test ADRs (ADR-109+) before generating")
    parser.add_argument("--clean-only", action="store_true", help="Remove generated test ADRs and exit")
    parser.add_argument("--index", action="store_true", help="Run decision-engine index after generating")
    args = parser.parse_args()

    if args.clean or args.clean_only:
        removed = 0
        for f in DECISIONS_DIR.glob("ADR-*.md"):
            num_match = __import__('re').match(r"ADR-(\d+)", f.stem)
            if num_match and int(num_match.group(1)) >= 109:
                f.unlink()
                removed += 1
        print(f"Removed {removed} test ADRs")
        if args.clean_only:
            return

    if args.start is not None:
        start = args.start
    else:
        import re
        max_num = 0
        for f in DECISIONS_DIR.glob("ADR-*.md"):
            m = re.match(r"ADR-(\d+)", f.stem)
            if m:
                max_num = max(max_num, int(m.group(1)))
        start = max_num + 1

    existing_ids = [f"ADR-{i:03d}" for i in range(1, start)]
    generated = 0

    for i in range(args.count):
        num = start + i
        adr_id = f"ADR-{num:03d}"
        filename, content = generate_adr(num, existing_ids)
        (DECISIONS_DIR / filename).write_text(content, encoding="utf-8")
        existing_ids.append(adr_id)
        generated += 1

    print(f"Generated {generated} ADRs (ADR-{start:03d} to ADR-{start+generated-1:03d})")

    if args.index:
        print("Indexing...")
        subprocess.run([sys.executable, str(SCRIPT_DIR / "decision-engine.py"), "index"])


if __name__ == "__main__":
    main()
