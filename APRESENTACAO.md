# Roteiro de apresentação

Sugestão de como conduzir a demonstração no laboratório. Ajuste conforme
o tempo disponível e o que o professor pedir.

## 1. Introdução (1 a 2 minutos)

"Esse trabalho estende o escalonador e o gerenciador de memória feitos
antes, adicionando um gerenciador de entrada e saída. Agora, enquanto um
processo está usando a CPU, ele pode pedir uma operação de E/S. Se pedir,
ele fica bloqueado até o dispositivo atender."

Mostrar rapidamente os arquivos: `simulador.py` (processo, CPU, E/S e
memória), `escalonadores.py` (algoritmos de escalonamento),
`substituidores.py` (algoritmos de substituição de página).

## 2. Mostrar o arquivo de entrada (2 minutos)

Abrir `entrada_ES.txt` e explicar as três partes: configuração geral,
lista de dispositivos, lista de processos. Apontar o campo
`chanceRequisitarES` no final da linha de cada processo.

## 3. Rodar o programa (3 a 5 minutos)

```
python3 simulador.py entrada_ES.txt
```

Ir apontando na tela:

- a linha "CPU: Pn", mostrando quem está rodando;
- a lista de "Prontos", com o tempo de CPU que falta para cada um;
- a lista de "Bloqueados", mostrando o dispositivo que cada processo está
  usando ou esperando;
- a lista de dispositivos, mostrando quem usa e quem espera cada um.

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

# Perguntas que o professor pode fazer, com resposta

**1. Como o programa decide se um processo vai pedir E/S?**

Toda vez que o processo é escolhido para rodar, o programa sorteia um
número de 1 a 100. Se esse número for menor ou igual à chance de E/S do
processo (lida do arquivo de entrada), ele vai pedir E/S nessa fatia. Se
vai pedir, o programa também sorteia qual dispositivo e depois de quantos
ciclos de CPU dentro da fatia isso acontece.

**2. O que acontece se o dispositivo sorteado já estiver em uso?**

O processo entra na fila de espera do dispositivo (`fila`, um `deque`
dentro da classe `DispositivoES`) e fica com estado "bloqueado" do mesmo
jeito que ficaria se já estivesse usando o dispositivo. Ele só volta a
concorrer pela CPU quando o dispositivo terminar de atender e ele for o
próximo da fila.

**3. Um processo bloqueado pode ser escolhido pelo escalonador?**

Não. Assim que o processo pede E/S, ele é retirado da estrutura do
escalonador (método `retirar`). Ele só volta a fazer parte da disputa
pela CPU quando a operação de E/S termina e o gerenciador de E/S chama
`chegada` de novo para ele.

**4. Por que existe um método `retirar` separado de `ao_terminar`, se os
dois removem o processo do escalonador?**

Porque as duas situações são diferentes para o escalonador de Prioridade
e para o CFS. No caso da Prioridade, o processo escolhido para rodar
continua no topo do heap enquanto executa, mas novos processos podem
chegar durante essa execução e mudar o que está no topo. Então, tanto ao
terminar quanto ao bloquear, o código precisa procurar e remover
especificamente o processo certo, não só "o que estiver no topo agora".
Separar os dois métodos deixa claro qual situação está sendo tratada em
cada ponto do código, mesmo quando a lógica interna é parecida.

**5. Como funciona a fila de espera de um dispositivo?**

Cada dispositivo guarda dois grupos: `em_uso` (processos sendo atendidos
agora) e `fila` (processos esperando, um `deque`, ou seja, uma fila
comum). A cada ciclo de tempo, o dispositivo primeiro atualiza quem está
em uso (diminuindo o tempo restante e liberando quem terminou) e depois
passa gente da fila para o uso, se sobrou vaga.

**6. Por que o dispositivo é sorteado aleatoriamente, e não escolhido pelo
processo?**

Porque o enunciado pede exatamente isso: quando o processo decide pedir
E/S, o dispositivo e o momento dentro da fatia são sorteados, não
escolhidos de forma determinística. Isso simula processos que não sabem
de antemão qual recurso vão precisar.

**7. O tempo que o processo passa esperando na fila de um dispositivo
conta como "bloqueado" ou como outra coisa?**

Conta como bloqueado. O enunciado só pede para diferenciar tempo em
pronto (esperando CPU) e tempo bloqueado (fazendo ou esperando E/S), sem
exigir uma categoria separada para "esperando o dispositivo ficar livre".
Por isso, tanto o tempo realmente usando o dispositivo quanto o tempo na
fila de espera contam como tempo bloqueado.

**8. O que aconteceria se dois processos pedissem o mesmo dispositivo no
mesmo instante de tempo?**

Como a simulação avança um ciclo de CPU de cada vez e só um processo usa
a CPU por vez, os pedidos de E/S acontecem em momentos diferentes na
prática (cada processo só pode pedir E/S enquanto está na CPU, e só um
processo está na CPU a cada momento). Então não existe empate real nesse
sentido. Quem pedir primeiro tem preferência para a vaga, e quem pedir
depois entra na fila se não sobrar vaga.

**9. Por que vocês trocaram a estrutura de dados da Loteria e do CFS?**

A versão anterior usava uma árvore de Fenwick para a Loteria e uma árvore
rubro-negra (biblioteca externa) para o CFS. Essas estruturas deixavam o
código mais difícil de explicar sem ganho real de desempenho para o
tamanho dos casos de teste do trabalho, e a árvore rubro-negra dependia
de uma biblioteca que não vem instalada por padrão no Python, o que é
arriscado num ambiente de correção. Trocamos por uma soma simples de
bilhetes para a Loteria e por uma fila de prioridade comum (heap da
biblioteca padrão) para o CFS, que fazem exatamente a mesma coisa de um
jeito mais direto de explicar.

**10. Como funciona o CFS aqui?**

Cada processo tem um `virtual_runtime`, que representa quanto ele já usou
de CPU, ajustado pela prioridade (que funciona como peso: quanto maior a
prioridade, mais devagar o virtual_runtime cresce, e mais vezes esse
processo tende a ser escolhido). O escalonador sempre escolhe quem tem o
menor `virtual_runtime` no momento, o que tende a equilibrar o uso de CPU
entre os processos ao longo do tempo.

**11. O que acontece com o `virtual_runtime` de um processo que bloqueia
para E/S no meio da fatia, antes de usar o quantum inteiro?**

Ele é atualizado com o tempo que o processo realmente usou até bloquear,
não com o quantum inteiro. Isso é importante porque, senão, um processo
que sempre pede E/S cedo na sua fatia pareceria ter usado menos CPU do
que realmente usou, e acabaria sendo escolhido com mais frequência do que
deveria pelo CFS.

**12. O que acontece se o arquivo de entrada tiver zero dispositivos de
E/S?**

O programa funciona normalmente, como nos trabalhos anteriores: nenhum
processo pede E/S, porque a checagem de chance de E/S já verifica se
existe algum dispositivo cadastrado antes de sortear.

**13. Como a memória e a E/S se relacionam nesse trabalho?**

Elas são praticamente independentes. A cada ciclo de CPU realmente
executado (ou seja, que não foi interrompido por um pedido de E/S), o
processo acessa uma página da sua sequência, e essa página é repassada
para o gerenciador de memória. Quando o processo está bloqueado, ele
simplesmente não acessa memória nesse período, porque não está usando a
CPU.

**14. Por que os quatro algoritmos de substituição de página rodam ao
mesmo tempo, em vez de só um?**

Isso já vinha do trabalho anterior: a ideia é comparar, ao final, qual
dos quatro algoritmos (FIFO, LRU, NUF, OPT) chega mais perto do resultado
do OPT, que é o algoritmo ótimo usado como referência. Cada um roda numa
simulação de memória separada, então o resultado de um não interfere no
outro.
