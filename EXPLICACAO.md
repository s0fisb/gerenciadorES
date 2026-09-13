# Explicação do código

Este arquivo explica como cada parte do código funciona, para ajudar na
apresentação e nas perguntas do professor.

## Visão geral

O programa lê o arquivo de entrada, monta os processos e os dispositivos,
e depois roda um laço principal que simula o tempo passando, um ciclo de
CPU de cada vez. A cada ciclo, o programa decide quem usa a CPU, atualiza
quem está esperando, atualiza quem está fazendo E/S, e acessa a memória.

## `Process`

Representa um processo. Guarda os dados do arquivo de entrada
(`exec_time`, `priority`, etc.) e também o estado que muda durante a
simulação:

- `remain_time`: quanto falta para o processo terminar
- `estado`: `"novo"`, `"pronto"`, `"executando"`, `"bloqueado"` ou
  `"terminado"`
- `waiting_time`: tempo total que já passou em "pronto"
- `blocked_time`: tempo total que já passou em "bloqueado"
- `dispositivo`: qual dispositivo está usando ou esperando, quando
  bloqueado
- `io_restante`: quanto falta para a operação de E/S atual terminar

## `DispositivoES` e `GerenciadorES`

Cada `DispositivoES` sabe quantos processos pode atender ao mesmo tempo
(`usos_simultaneos`) e quanto tempo demora uma operação (`tempo_operacao`).
Ele guarda dois grupos de processos:

- `em_uso`: processos usando o dispositivo agora
- `fila`: processos esperando a vez

Quando um processo pede o dispositivo (`solicitar`), se ainda tem vaga em
`em_uso`, ele começa a usar na hora. Se não tem vaga, ele entra na `fila`
e fica esperando.

A cada ciclo de tempo, `avancar()` faz duas coisas: diminui o tempo
restante de quem está usando o dispositivo (e libera quem terminou), e
depois passa quem está esperando na fila para o uso, se sobrou vaga.

O `GerenciadorES` é só quem organiza todos os dispositivos juntos: recebe
os pedidos de E/S e repassa para o dispositivo certo, e manda todos os
dispositivos avançarem um ciclo de cada vez.

## Como o processo decide pedir E/S

Isso acontece dentro de `CPU.executar_processo`, toda vez que um processo
começa a rodar:

1. Sorteia um número de 1 a 100. Se for menor ou igual à `chance_es` do
   processo, ele vai pedir E/S nessa fatia de CPU.
2. Se vai pedir, sorteia em qual dispositivo (`escolher_dispositivo`) e
   depois de quantos ciclos de CPU dentro da fatia isso vai acontecer
   (`momento_es`, um número entre 1 e o tamanho do quantum).
3. O processo executa ciclo por ciclo. Depois de executar o ciclo número
   `momento_es`, ele para, pede o dispositivo e volta para o laço
   principal como processo bloqueado.

Se o processo não tiver E/S sorteada para essa fatia, ele simplesmente
roda até o fim do quantum ou até terminar, como nos trabalhos anteriores.

## Escalonadores (`escalonadores.py`)

Todos seguem a mesma interface (classe abstrata `Escalonador`):

- `chegada(processo)`: processo entra na estrutura (chegou ou voltou de
  E/S)
- `selecionar()`: escolhe o próximo processo a rodar
- `ao_terminar(processo)`: processo terminou, remove ele
- `retirar(processo)`: processo bloqueou para E/S, remove ele
- `apos_quantum(processo)`: processo usou o quantum inteiro sem terminar

O método `retirar` é a parte nova por causa da E/S: antes, um processo só
saía do escalonador quando terminava. Agora ele também pode sair porque
foi bloqueado, então cada escalonador precisa saber tirar um processo do
meio da sua estrutura, não só do começo ou do topo.

- **Alternância Circular (Round-Robin)**: fila simples (lista). O
  ponteiro `_idx` marca de quem é a vez.
- **Prioridade**: fila de prioridade (heap) de tuplas
  `(prioridade, ordem_chegada, processo)`. O `selecionar` só olha o topo
  do heap, sem remover, porque durante a execução do processo escolhido
  outros processos podem chegar e mudar quem está no topo. Por isso,
  tanto `ao_terminar` quanto `retirar` procuram o processo certo pela
  identidade dele dentro do heap, em vez de simplesmente tirar o que
  estiver no topo naquele momento.
- **Loteria**: cada processo tem uma quantidade de bilhetes igual à sua
  prioridade. Os bilhetes ficam guardados numa árvore de Fenwick (Binary
  Indexed Tree, classe `FenwickTree`), que mantém somas parciais dos
  bilhetes. Para sortear, sorteia-se um número entre 1 e o total de
  bilhetes e a árvore encontra "de quem é o bilhete k" em tempo
  logarítmico (`find_kth`), em vez de percorrer a lista de processos um
  por um. Isso é o que permite o sorteio continuar rápido mesmo com muitos
  processos.
- **CFS**: versão simplificada do escalonador do Linux. Cada processo tem
  um `virtual_runtime`, que cresce conforme ele usa CPU (multiplicado
  pela prioridade, que funciona como peso). O escalonador sempre escolhe
  quem tem o menor `virtual_runtime`, guardado numa árvore rubro-negra
  (`RBTree`, da biblioteca `bintrees`) — a mesma estrutura de dados que o
  CFS real do kernel Linux usa para isso. Aqui, diferente da Prioridade, o
  `selecionar` já remove o processo da árvore, porque a ordem de escolha
  não muda durante a execução do processo (a árvore só volta a mudar
  depois que ele terminar a fatia ou bloquear).

## Gerenciador de memória (`substituidores.py` e a parte de memória do
`memoria_versãofinal_agoravai.py`)

Essa parte não mudou desde o trabalho anterior. Os quatro algoritmos de
substituição (FIFO, LRU, NUF, OPT) rodam em paralelo, cada um com sua
própria contagem de trocas de página, para no final comparar qual chegou
mais perto do OPT (referência ótima). A política pode ser local (cada
processo tem sua fatia fixa de memória) ou global (todos disputam o mesmo
conjunto de molduras).

## Laço principal (`CPU.run`)

A cada volta do laço:

1. Admite processos novos que já chegaram (`admitir_novo_processo`).
2. Se não tem ninguém pronto, mas também não tem ninguém bloqueado nem
   por chegar, a simulação terminou.
3. Se não tem ninguém pronto mas tem gente bloqueada ou por chegar, o
   tempo avança sem usar a CPU (`avancar_tempo_sem_cpu`), só para os
   dispositivos e a fila de novos processos evoluírem.
4. Se tem alguém pronto, o escalonador escolhe quem roda, o estado muda
   para `"executando"`, o estado do sistema é impresso, e o processo roda
   uma fatia de CPU.
5. Depois da fatia, dependendo do que aconteceu (terminou, bloqueou ou só
   usou o quantum), o escalonador é avisado do jeito certo
   (`ao_terminar`, `retirar` ou `apos_quantum`).

A cada ciclo de tempo dentro da fatia, o programa também chama
`atualizar_bloqueados`, que soma o tempo de bloqueio de quem está
bloqueado e avança os dispositivos de E/S, e `admitir_novo_processo`,
que verifica se algum processo novo acabou de chegar.

## Por que a impressão do estado muda antes de imprimir

O processo escolhido pelo escalonador só é marcado como `"executando"`
antes da chamada que imprime o estado do sistema. Se isso não fosse
feito nessa ordem, o processo apareceria ao mesmo tempo como "CPU: Pn" e
na lista de prontos, porque ainda estaria com o estado antigo no momento
da impressão.

## Por que a pré-simulação do OPT também precisa simular a E/S

Na política global de memória, o algoritmo OPT (ótimo) decide qual página
remover olhando para uma simulação prévia da ordem em que as páginas
serão acessadas (`construir_sequencia_futura`). Essa pré-simulação roda o
mesmo escalonamento e a mesma E/S que a simulação real vai rodar depois —
e não só o escalonamento, como numa versão anterior.

O motivo é que a E/S muda quem executa em seguida, não só o instante no
relógio: um processo pode bloquear no meio da fatia e ceder a CPU mais
cedo do que cederia sem E/S, adiantando a vez de outro processo. Isso
muda a ordem em que os acessos de processos diferentes se intercalam.
Se a pré-simulação ignorasse a E/S, o OPT decidiria vítimas com base
numa sequência futura que não é a que realmente vai acontecer — e nesse
caso o OPT deixa de ser garantidamente ótimo, podendo inclusive fazer
mais trocas que um algoritmo não-ótimo (o que não faz sentido para uma
referência "ótima").

Para a pré-simulação reproduzir exatamente a mesma sequência de acessos
que a simulação real, os sorteios de E/S (se o processo pede E/S, qual
dispositivo, em que momento da fatia) precisam ser os mesmos nas duas.
Por isso o estado do gerador de números aleatórios é salvo antes da
pré-simulação e restaurado logo depois: a simulação real, que roda em
seguida, sorteia exatamente os mesmos valores e caminha pelos mesmos
eventos, então a sequência pré-calculada bate com a real.
