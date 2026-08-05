# ADR 0001: Redis Streams como message broker (com Kafka como caminho de evolução)

## Contexto
O pipeline precisa desacoplar os workers de ingestão dos workers de
processamento e do RAG engine, para que uma falha ou lentidão em um
consumidor não derrube o produtor nem perca eventos.

## Decisão
Usar Redis Streams para desenvolvimento local e como padrão inicial de
produção, com consumer groups para permitir múltiplas réplicas de cada
worker dividindo a carga automaticamente.

## Alternativas consideradas
- **Kafka**: mais robusto para altíssimo throughput e retenção longa de
  eventos, mas exige operar Zookeeper/KRaft, mais peças móveis para um
  projeto de portfólio rodando em cluster pequeno.
- **RabbitMQ**: bom para filas de tarefas, mas Streams do Redis já cobre o
  padrão pub/sub com replay que o projeto precisa, e o Redis já é usado
  como cache/estado, evitando mais um componente de infraestrutura.

## Consequências
- Menos operação no dia a dia, ideal para demonstrar o projeto rodando.
- Redis Streams tem menor throughput teórico que Kafka; se o volume de
  ticks crescer muito, a migração para Kafka é um passo natural de
  evolução documentado aqui (o contrato de mensagens já é serializável em
  JSON, então a migração é sobretudo de infraestrutura, não de código de
  domínio).
