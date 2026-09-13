# Roteiro de apresentação

Sugestão de como conduzir a demonstração no laboratório. Ajuste conforme
o tempo disponível e o que o professor pedir.

## 1. Introdução (1 a 2 minutos)

"Esse trabalho estende o escalonador e o gerenciador de memória feitos
antes, adicionando um gerenciador de entrada e saída. Agora, enquanto um
processo está usando a CPU, ele pode pedir uma operação de E/S. Se pedir,
ele fica bloqueado até o dispositivo atender."

Mostrar rapidamente os arquivos: `memoria_versãofinal_agoravai.py`
(processo, CPU, E/S e memória), `escalonadores.py` (algoritmos de
escalonamento), `substituidores.py` (algoritmos de substituição de
página).

## 2. Mostrar o arquivo de entrada (2 minutos)

Abrir `entrada_ES.txt` e explicar as três partes: configuração geral,
lista de dispositivos, lista de processos. Apontar o campo
`chanceRequisitarES` no final da linha de cada processo.

## 3. Rodar o programa (3 a 5 minutos)

```
python3 "memoria_versãofinal_agoravai.py" entrada_ES.txt
```

Ir apontando na tela, em cada painel (um por troca real de processo na CPU,
com o relógio no título — `t=<tempo> — Pn assume a CPU`):

- a linha "Executando", mostrando quem está rodando e o tempo de CPU que
  falta pra ele terminar;
- a lista de "Prontos", com o tempo de CPU que falta para cada um;
- a lista de "Bloqueados", mostrando o dispositivo que cada processo está
  usando ou esperando;
- a lista de dispositivos, com o estado (livre / parcialmente ocupado /
  ocupado) e quem usa e quem espera cada um.

Se possível, esperar aparecer um momento em que um dispositivo tem fila
de espera (mais de um processo querendo o mesmo dispositivo ao mesmo
tempo), para mostrar que o segundo processo espera.

Ao final, mostrar as linhas de resumo de cada processo
(`total`, `pronto`, `bloqueado`) e a linha final com o total de trocas de
página de cada algoritmo de substituição.

## 4. Trocar o algoritmo de escalonamento (opcional, 2 minutos)

Editar a primeira linha do arquivo de entrada (por exemplo, trocar
`alternancia` por `prioridade` ou `cfs`) e rodar de novo, para mostrar que
o gerenciador de E/S funciona do mesmo jeito com qualquer escalonador.

## 5. Encerramento

Reforçar que o gerenciador de E/S foi pensado para ser independente do
escalonador escolhido, e que os quatro algoritmos de substituição de
página continuam rodando em paralelo para efeito de comparação.

---

# Perguntas que o professor pode fazer sobre a E/S, com resposta

Organizadas por tema. O foco é lógica e estruturas de dados, não
detalhamento de sintaxe — os nomes de classe/método entre parênteses são
só para achar o trecho no código se precisar.

## Visão geral

**0. Em linhas gerais, o que a E/S mudou no simulador em relação ao
trabalho anterior?**

Antes, um processo só saía da CPU por dois motivos: terminou, ou usou o
quantum inteiro. Agora existe um terceiro motivo: pediu E/S e precisa
esperar um dispositivo. Isso exigiu três coisas novas: (1) um sorteio, a
cada vez que o processo é escolhido para rodar, decidindo se/quando/onde
ele vai pedir E/S; (2) uma estrutura pra representar os dispositivos, com
capacidade e fila de espera; e (3) um jeito de tirar um processo bloqueado
do meio da estrutura de cada escalonador (não só do topo/início, como já
acontecia para "terminou"), e devolvê-lo lá depois.

## Lógica de decisão (quando, qual dispositivo, em que momento)

**1. Como o programa decide se um processo vai pedir E/S?**

Toda vez que o processo é escolhido para rodar (`CPU.executar_processo`,
início da fatia), o programa sorteia um número de 1 a 100. Se esse número
for menor ou igual à `chance_es` do processo (lida do arquivo de
entrada), ele vai pedir E/S nessa fatia — o sorteio é refeito a cada nova
vez que o processo assume a CPU, não uma vez só na vida dele.

**2. Se ele vai pedir E/S, como o programa decide qual dispositivo e em
que momento da fatia isso acontece?**

Mais dois sorteios, feitos de uma vez, antes do processo começar a
executar os ciclos daquela fatia: um dispositivo é sorteado entre todos
os existentes (`escolher_dispositivo`, com a mesma chance para todos), e
um número entre 1 e o tamanho do quantum é sorteado como o "momento" —
depois de executar esse tanto de ciclos dentro da fatia, o processo para
e pede o dispositivo.

**3. Por que o dispositivo e o momento são sorteados, em vez de
escolhidos pelo processo?**

Porque é isso que o enunciado pede: o processo não sabe de antemão qual
recurso vai precisar nem quando. Sortear simula essa incerteza, em vez de
um comportamento determinístico e previsível.

**4. O que acontece se o `momento_es` sorteado for maior que o tempo que
falta para o processo terminar?**

Nada de especial acontece: o processo simplesmente termina antes de
chegar nesse ciclo, porque a checagem de "processo terminou" é feita a
cada ciclo, antes da checagem de "chegou a hora de pedir E/S". Ele nunca
chega a pedir E/S — o sorteio foi feito, mas não teve efeito.

## Estruturas de dados

**5. Que estruturas representam um dispositivo e o conjunto de
dispositivos?**

`DispositivoES` guarda `usos_simultaneos` (capacidade), `tempo_operacao`,
e dois grupos de processos: `em_uso` (lista) e `fila` (um `deque`, fila
FIFO). `GerenciadorES` é só um dicionário `{id: DispositivoES}` que
recebe os pedidos e repassa para o dispositivo certo, e manda todos
avançarem um ciclo de cada vez.

**6. Como funciona a fila de espera de um dispositivo, na prática?**

Quando um processo pede o dispositivo (`solicitar`): se `em_uso` ainda
tem vaga (menos processos que `usos_simultaneos`), ele entra direto em
uso. Senão, entra no fim da `fila` (deque) e espera. A cada ciclo de
tempo, `avancar()` faz duas coisas em ordem: primeiro desconta o tempo
restante de quem está em uso e libera quem terminou, depois passa gente
da fila para as vagas que sobraram — então uma vaga liberada nesse mesmo
ciclo já pode ser ocupada por quem estava na frente da fila, sem esperar
um ciclo extra parado.

**7. Como o programa sabe quanto tempo falta para uma operação de E/S
terminar?**

Cada processo tem um campo `io_restante`. Quando ele começa a usar um
dispositivo (seja na hora do pedido, seja saindo da fila depois), esse
campo recebe o `tempo_operacao` do dispositivo. A cada ciclo,
`avancar()` desconta 1 de `io_restante` de cada processo em uso; quando
chega a 0, o processo é liberado.

**8. Que campos o `Process` ganhou por causa da E/S?**

`estado` (novo/pronto/executando/bloqueado/terminado — os dois últimos já
existiam, mas "bloqueado" é novo), `dispositivo` (qual dispositivo está
usando ou esperando, só relevante quando bloqueado) e `io_restante`
(tempo restante da operação atual).

## Interação com o escalonamento

**9. Como o programa impede que um processo bloqueado seja escolhido de
novo para a CPU?**

No momento em que o processo pede E/S, ele é fisicamente retirado da
estrutura de dados do escalonador (`retirar`) — lista do Round-Robin,
heap da Prioridade, árvore de Fenwick da Loteria ou árvore rubro-negra do
CFS. Como o `selecionar()` de cada escalonador só enxerga o que está
dentro da própria estrutura, um processo removido dali simplesmente não
é mais uma opção, mesmo que o objeto `Process` continue existindo na
lista geral de processos.

**10. Como um processo bloqueado volta a disputar CPU depois que sai do
dispositivo (ou da fila)?**

`GerenciadorES.avancar()` devolve a lista de quem terminou de usar algum
dispositivo naquele ciclo. `CPU.atualizar_bloqueados` pega essa lista e
chama `chegada(processo)` no escalonador para cada um — exatamente o
mesmo método usado quando um processo chega pela primeira vez, então ele
volta a competir pela CPU do zero, sem tratamento especial.

**11. Por que existe um método `retirar` separado de `ao_terminar`, se os
dois tiram o processo do escalonador?**

Porque nem toda estrutura remove do mesmo jeito nos dois casos. Na
Prioridade, por exemplo, o processo escolhido continua no topo do heap
enquanto executa (pra não pagar o custo de removê-lo e reinseri-lo à toa
se ele terminar o quantum inteiro), mas chegadas de outros processos
durante essa execução podem mudar quem está no topo — então tanto
`ao_terminar` quanto `retirar` precisam procurar e remover
especificamente o processo certo, não "o que estiver no topo agora".
Separar os métodos deixa claro qual situação está sendo tratada em cada
ponto, mesmo quando a lógica de busca é parecida.

**12. Enquanto um processo está bloqueado em E/S, o que acontece com os
outros processos prontos?**

Continuam disputando a CPU normalmente, pela política do escalonador
escolhido — bloquear um processo não pausa os outros. É por isso que o
laço principal processa "um processo por vez, um ciclo por vez": a cada
ciclo de CPU de algum processo em execução, `atualizar_bloqueados` também
avança os dispositivos, então bloqueados e prontos evoluem juntos.

**13. O que o programa faz quando não sobra ninguém pronto, mas ainda tem
gente bloqueada ou por chegar?**

Existe um caminho separado no laço principal (`avancar_tempo_sem_cpu`):
o relógio avança sozinho, sem ninguém usando a CPU, só atualizando os
dispositivos de E/S e checando se algum processo novo chega ou algum
bloqueado se libera — até sobrar alguém pronto de novo (ou a simulação
acabar, se não sobrar mais ninguém em lugar nenhum).

**14. Por que a Loteria usa uma árvore de Fenwick e o CFS usa uma árvore
rubro-negra pra guardar os processos?**

Pro tamanho dos casos de teste do trabalho, uma lista simples resolveria
sem diferença visível no resultado — a escolha é para o simulador se
aproximar do que um SO real faz, não só do resultado final. Na Loteria,
sortear um bilhete com lista exigiria somar bilhete por bilhete até
passar do número sorteado (custo linear); a árvore de Fenwick guarda
somas parciais e acha "de quem é o bilhete k" em tempo logarítmico. No
CFS, a árvore rubro-negra é literalmente a estrutura que o CFS do kernel
Linux usa pra guardar processos ordenados por `vruntime` e achar o menor
valor rápido — um heap comum até funcionaria aqui, mas não seria fiel ao
mecanismo real. Essas duas estruturas são também o motivo de `retirar`
precisar de uma implementação por escalonador: remover do meio de uma
árvore de Fenwick, de uma RBTree ou de um heap são operações diferentes.

**15. O que acontece com o `virtual_runtime` (CFS) de um processo que
bloqueia no meio da fatia, antes de usar o quantum inteiro?**

Ele é atualizado só com o tempo que o processo realmente usou até
bloquear (`pos_execucao`, chamado com `executado`, não com o quantum
cheio). Sem isso, um processo que sempre pede E/S cedo pareceria ter
usado menos CPU do que realmente usou, e o CFS passaria a escolhê-lo com
mais frequência do que deveria.

## Interação com a memória

**16. Como a memória e a E/S se relacionam?**

São praticamente independentes, mas só uma acontece por ciclo: a cada
ciclo de CPU realmente executado (isto é, um ciclo em que o processo
estava rodando, não bloqueado), ele acessa uma página da sua sequência,
repassada pro gerenciador de memória. Enquanto está bloqueado, o processo
não acessa memória nenhuma, porque não está usando a CPU — só o tempo
passa.

**17. Por que a pré-simulação do algoritmo OPT (política de memória
global) também precisa simular a E/S, e não só o escalonamento?**

O OPT decide qual página remover olhando pra uma sequência futura de
acessos pré-calculada (`construir_sequencia_futura`). Um processo que
bloqueia por E/S no meio da fatia cede a CPU mais cedo do que cederia sem
E/S, o que muda quem executa em seguida — e portanto muda a ordem em que
os acessos de processos diferentes se intercalam. Se a pré-simulação
ignorasse a E/S, a sequência calculada não seria a que realmente vai
acontecer, e o OPT deixaria de ser garantidamente ótimo (podendo até
fazer mais trocas que um algoritmo não-ótimo). Pra pré-simulação bater
exatamente com a simulação real, os três sorteios de E/S (pede ou não,
qual dispositivo, que momento) precisam sair iguais nas duas — por isso o
estado do gerador de números aleatórios é salvo antes da pré-simulação e
restaurado logo depois, e a simulação real sorteia exatamente os mesmos
valores em seguida.

## Contagem de tempo e casos de borda

**18. Como é contado o tempo que o processo passa bloqueado, pronto e
executando?**

Três contadores no próprio `Process`: `running_time` aumenta a cada ciclo
real de CPU usado; `waiting_time` aumenta, a cada ciclo, para todo
processo pronto que não é o que está executando; `blocked_time` aumenta a
cada ciclo em que o processo está com estado "bloqueado" — usando ou
esperando um dispositivo, não importa qual dos dois.

**19. No resumo final de cada processo, vocês mostram tempo total, tempo
pronto e tempo bloqueado. Como cada um desses três valores é contado
durante a simulação, e o que garante que a soma dos três bate com o
tempo total?**

A contagem é a mesma da pergunta anterior: `running_time`,
`waiting_time` e `blocked_time`, cada um incrementado por um mecanismo
diferente (execução real, `incrementar_espera`, `atualizar_bloqueados`).
Mas o que **garante** a soma bater não é a fórmula em si, é uma
invariante de desenho da simulação: a cada unidade de tempo, o processo
está em exatamente um desses três estados — nunca em zero, nunca em mais
de um. Executando, pronto e bloqueado se excluem mutuamente a cada
ciclo, e cada ciclo incrementa exatamente um dos três contadores. Como
os três casos cobrem tudo que pode acontecer com um processo entre a
criação e o término, e nunca se sobrepõem, a soma dos três é, por
construção, igual ao tempo total (`finish_time - start`).

**20. O tempo que o processo passa na fila de espera de um dispositivo
(antes de começar a ser atendido) conta como bloqueado ou como outra
categoria?**

Conta como bloqueado. O enunciado só pede pra diferenciar pronto
(esperando CPU) de bloqueado (fazendo ou esperando E/S), sem exigir uma
categoria separada pra "esperando o dispositivo ficar livre". Por isso o
processo já entra com `estado = "bloqueado"` no momento do pedido, esteja
ele em uso ou só na fila.

**21. O que aconteceria se dois processos pedissem o mesmo dispositivo no
mesmo instante de tempo?**

Não existe empate real: a simulação processa um ciclo de CPU de um
processo por vez, e só um processo pode estar executando a cada momento
— então os pedidos de E/S nunca acontecem literalmente ao mesmo tempo,
sempre em instantes diferentes da simulação. Quem pede primeiro tem
preferência pela vaga; quem pede depois entra atrás na fila, e o `deque`
preserva essa ordem de chegada naturalmente.

**22. O que acontece se o arquivo de entrada tiver zero dispositivos de
E/S?**

O programa funciona normalmente, como nos trabalhos anteriores: nenhum
processo pede E/S, porque o sorteio de "vai pedir E/S?" já checa se
existe algum dispositivo cadastrado antes de rodar (`bool(dispositivos)`)
— sem essa checagem, sortear um dispositivo de uma lista vazia quebraria
o programa.

## Saída na tela

**23. O que aparece na tela a cada troca de processo na CPU?**

Um painel: um título com o relógio da simulação e quem assumiu a CPU
(`t=<tempo> — Pn assume a CPU`), a linha "Executando" com o tempo
restante desse processo, "Prontos" e "Bloqueados" com o tempo restante de
cada um (e o dispositivo, para os bloqueados), e a lista de dispositivos
com estado (livre / parcialmente ocupado / ocupado) e quem está usando ou
esperando cada um.

**24. O painel aparece só quando um processo novo assume a CPU, ou também
no meio da fatia (por exemplo, quando alguém bloqueia por E/S antes de
terminar o quantum)?**

Só quando um processo novo assume a CPU — uma troca real. Quando um
processo bloqueia no meio da fatia, ele simplesmente devolve o controle
pro laço principal, que já vai escolher o próximo processo e imprimir o
próximo painel; não existe um painel extra só pra marcar o bloqueio. Isso
segue literalmente o enunciado ("a cada vez que for trocar o processo em
execução"), e a informação de quem bloqueou não se perde: ela aparece no
próximo painel, na lista de bloqueados.

---

# Chance de cada pergunta cair na arguição

O professor disse que faz só 4 perguntas, as mesmas pra todo grupo, focadas
em como a E/S foi implementada (não em escalonador/memória puros, já
avaliados em bimestres anteriores). A tabela abaixo ordena as 25 perguntas
acima da mais pra menos provável de estar entre essas 4, com o motivo.

Critério: prioridade pra pergunta que mapeia direto numa frase do
enunciado e é fácil de checar em qualquer grupo, independente de detalhe
de implementação. Perguntas que são mais sobre "onde no código" do que
"por quê", ou que dependem de uma escolha específica de vocês (não do
enunciado), ficam mais abaixo.

| # | Pergunta (resumo) | Chance | Por quê |
|---|---|---|---|
| 1 | Como decide se um processo pede E/S | **Muito alta** | É a primeira coisa que o enunciado pede sobre E/S; quase impossível não perguntar isso de alguma forma |
| 9 | Como impede um processo bloqueado de ser escolhido de novo | **Muito alta** | Frase mais crítica do enunciado ("não poderá ser escalonado") |
| 6 | Como funciona a fila de espera na prática | **Muito alta** | Comportamento mais visual e demonstrável; o próprio roteiro de vocês sugere mostrar isso ao vivo |
| 18 | Como é contado pronto/bloqueado/execução | **Muito alta** | Último parágrafo do enunciado, entrega obrigatória do resultado final |
| 2 | Como decide qual dispositivo é sorteado | Alta | Extensão direta da pergunta 1, mesma frase do enunciado |
| 3 | Como decide o momento da fatia em que a E/S ocorre | Alta | Mesma frase do enunciado que a 2 |
| 12 | O que acontece com os outros processos prontos enquanto um bloqueia | Alta | Frase explícita do enunciado ("devem prosseguir com a execução normalmente") |
| 10 | Como o processo volta a disputar CPU depois da E/S | Alta | Fecha o ciclo da pergunta 9, mesmo nível de importância |
| 17 | Por que a pré-simulação do OPT também precisa simular E/S | Alta | O achado mais rico e defensável da sessão (números concretos de quando dá errado), mas é mais avançada que as de cima |
| 19 | O que garante que pronto + bloqueado + execução bate com o total | Alta | Pergunta natural de aprofundamento da 18 — mas o professor tende a escolher uma das duas, não as duas |
| 23 | O que aparece na tela a cada troca de processo | Alta | Requisito explícito de exibição, parágrafo inteiro do enunciado dedicado a isso |
| 4 | O que acontece se o momento sorteado for maior que o tempo restante | Média | Caso de borda rápido e charmoso de perguntar (o tipo de "pegadinha" que professor gosta) |
| 20 | Fila de espera conta como bloqueado ou outra categoria | Média | Detalhe específico, mas pergunta comum sobre contagem de tempo |
| 11 | Por que `retirar` é separado de `ao_terminar` | Média | Pergunta boa e reveladora, mas mais arquitetural/demorada de responder bem em pouco tempo |
| 13 | O que acontece quando ninguém está pronto mas tem gente bloqueada | Média | Caso de borda razoável, mas menos central que os "Tier 1" |
| 16 | Como memória e E/S se relacionam | Média | Repete parte do conteúdo da pergunta 17 — professor tende a escolher uma das duas |
| 21 | O que acontece se dois processos pedem o mesmo dispositivo no mesmo instante | Média | Caso de borda mais "filosófico" (resposta é "isso não acontece de verdade") |
| 22 | O que acontece com zero dispositivos de E/S | Média | Caso de borda de robustez, mas simples de responder |
| 15 | O que acontece com o `virtual_runtime` do CFS ao bloquear | Baixa | Só é relevante se o grupo estiver demonstrando o CFS especificamente |
| 5 | Que estruturas representam um dispositivo | Baixa | Pergunta mais sobre "onde" está a informação do que "por quê" a lógica funciona assim |
| 0 | Visão geral do que a E/S mudou | Baixa | Mais introdução/quebra-gelo do que avaliação de profundidade; com só 4 perguntas o professor tende a ir direto ao ponto |
| 24 | Painel aparece só na troca real, não no meio do bloqueio | Baixa | Detalhe de interface bem miúdo |
| 7 | Como o programa sabe quanto falta pra E/S terminar (`io_restante`) | Baixa | Detalhe mecânico específico demais pra uma de só 4 perguntas |
| 8 | Que campos o `Process` ganhou por causa da E/S | Baixa | Detalhe mecânico, mais "o quê" do que "por quê" |
| 14 | Por que a Loteria usa Fenwick e o CFS usa árvore rubro-negra | **Muito baixa** | É uma escolha de estrutura de dados do **escalonador**, feita num bimestre anterior — pelo critério do próprio professor ("memória e processos já avaliados"), essa é a mais fora de escopo, a não ser que ele puxe gancho com a 11 |

**Se fosse apostar nas 4 que realmente caem:** 1, 9, 6 e 18 — sozinhas, cobrem quase todo o parágrafo de E/S do enunciado.