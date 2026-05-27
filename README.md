# Лабораторная работа 14 — Вариант 4 (Повышенная сложность) — Ведешкин Андрей Георгиевич — группа 221131

Предметная область: **парсинг новостных сайтов (RSS + HTML)**.

---

## Общая структура проекта

```text
./
├── scraper-go/              # Go-сборщик (etcd, tumbling window, Arrow Flight, Kafka/NATS, метрики)
│   ├── main.go
│   ├── etcd_coordinator.go
│   ├── aggregator.go
│   ├── arrow_flight.go
│   ├── broker.go
│   ├── validator.go
│   └── Dockerfile
├── scraper-python/          # Python-сборщик (asyncio/aiohttp) для сравнения производительности
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
├── analyzer/                # Python-анализатор (Kafka/NATS consumer, sliding window, API, Arrow client)
│   ├── consumer.py
│   ├── sliding_window.py
│   ├── arrow_client.py
│   ├── api.py
│   └── Dockerfile
├── validator-rust/          # Rust-библиотека валидации + C FFI
│   ├── src/lib.rs
│   ├── include/news_validator.h
│   └── Cargo.toml
├── dashboard/               # Streamlit-дашборд с обновлением в реальном времени
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── benchmarks/              # Сценарии сравнения Go vs Python + отчеты/графики
│   ├── load_test_go.py
│   ├── load_test_python.py
│   └── compare_results.py
├── infra/                   # Инфраструктура (Docker Compose + Kubernetes + HPA)
│   ├── docker-compose.yml
│   └── k8s/
│       ├── namespace.yaml
│       ├── scraper-go.yaml
│       ├── analyzer.yaml
│       ├── dashboard.yaml
│       ├── etcd.yaml
│       ├── kafka.yaml
│       └── hpa.yaml
└── README.md
```

---

## Реализованные задания повышенной сложности

| № | Задание | Реализация в проекте |
|---|---------|----------------------|
| 1 | **Распределенный сборщик на Go (etcd)** | В `scraper-go/etcd_coordinator.go` реализована регистрация воркеров, heartbeats, блокировки источников и распределение источников между экземплярами. |
| 2 | **Оконная агрегация в Go (tumbling window)** | В `scraper-go/aggregator.go` реализованы временные/счетные окна, принудительный flush, вычисление агрегатов (кол-во статей, средние длины, частоты источников). |
| 3 | **Передача данных через Apache Arrow** | В `scraper-go/arrow_flight.go` поднят Arrow Flight сервер, который отдает агрегированные окна как `RecordBatch`; клиентская часть есть в `analyzer/arrow_client.py`. |
| 4 | **Интеграция Rust-библиотеки для валидации** | В `validator-rust/src/lib.rs` реализована валидация полей и C-интерфейс; в `scraper-go/validator.go` подключение через `cgo` и вызов Rust-валидатора для статей. |
| 5 | **Развертывание в Kubernetes с автоскалированием** | В `infra/k8s/` есть манифесты сервисов; `infra/k8s/hpa.yaml` задает `HorizontalPodAutoscaler` для `scraper-go` (масштабирование по CPU/Memory). |
| 6 | **Сравнение производительности Go vs Python** | В `benchmarks/` реализованы нагрузочные прогоны и сравнение метрик CPU/RAM/времени; `compare_results.py` строит отчет и графики (`png`). |
| 7 | **Потоковая обработка через Kafka/NATS** | В `scraper-go/broker.go` реализованы паблишеры для Kafka/NATS; в `analyzer/consumer.py` — консюмеры обоих брокеров и потоковая обработка в `sliding_window.py`. |
| 8 | **Веб-дашборд в реальном времени** | В `dashboard/app.py` реализован Streamlit-интерфейс с автообновлением, графиками и подключением к API анализатора. |

---

## Взаимодействие с проектом

### Требования

- Docker + Docker Compose
- Go 1.21+
- Python 3.9+
- Rust (stable) + Cargo
- (Опционально) Kubernetes + metrics-server для HPA

### Запуск всей системы через Docker Compose

```bash
cd infra
docker-compose up --build
```

После запуска доступны:

- Dashboard: `http://localhost:8501`
- Analyzer API: `http://localhost:8000`
- Kafka UI: `http://localhost:8080`
- NATS monitoring: `http://localhost:8222`
- Arrow Flight endpoint (gRPC): `localhost:8815`

---

## Проверка ключевых компонентов

### 1) Go-сборщик + etcd координация

Логи `scraper-go` показывают подключение к etcd, регистрацию источников и lock/unlock для источников:

```bash
docker-compose -f infra/docker-compose.yml logs -f scraper-go
```

### 2) Tumbling window агрегация

В логах `scraper-go` видны события flush окна и агрегированные метрики:

```bash
docker-compose -f infra/docker-compose.yml logs -f scraper-go
```

### 3) Arrow Flight передача

`analyzer` может читать агрегаты через `analyzer/arrow_client.py`; при включенном `ARROW_FLIGHT_ENABLED=true` данные доступны из Flight-сервера `scraper-go`.

### 4) Rust-валидация

Сборка валидатора:

```bash
cd validator-rust
cargo build --release
```

После этого `scraper-go` использует библиотеку через cgo (см. `scraper-go/validator.go`).

### 5) Kafka/NATS стриминг

- Источник сообщений: `scraper-go`
- Потребитель сообщений: `analyzer/consumer.py`
- Оконная аналитика: `analyzer/sliding_window.py` (скользящее окно)

Переключение брокера задается переменными окружения (`BROKER_TYPE=kafka|nats`).

### 6) Бенчмарки Go vs Python

```bash
cd benchmarks
pip install -r requirements.txt
python load_test_python.py
python load_test_go.py
python compare_results.py
```

Результаты сохраняются в `benchmarks/benchmark_results/`:

- метрики прогонов (`*.json`)
- текстовый отчет (`performance_comparison_report.txt`)
- графики (`performance_comparison.png`, `improvement_ratios.png`)

---

## Kubernetes + HPA

Применение манифестов:

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/etcd.yaml
kubectl apply -f infra/k8s/kafka.yaml
kubectl apply -f infra/k8s/scraper-go.yaml
kubectl apply -f infra/k8s/analyzer.yaml
kubectl apply -f infra/k8s/dashboard.yaml
kubectl apply -f infra/k8s/hpa.yaml
```

Проверка HPA:

```bash
kubectl get hpa -n news-scraper
kubectl describe hpa scraper-go-hpa -n news-scraper
```

---

## Итоги

В проекте реализован полный конвейер новостного парсинга и анализа:

- распределенный Go-сбор данных с координацией через etcd;
- оконная агрегация и бинарная передача агрегатов через Apache Arrow Flight;
- интеграция Rust-валидации через cgo;
- потоковая обработка через Kafka/NATS;
- сравнение производительности Go и Python;
- развертывание в Docker/Kubernetes с HPA;
- веб-дашборд с обновлением в реальном времени.