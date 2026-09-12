# Como executar

Dependências: Python 3 e a biblioteca `bintrees` (usada para a árvore
rubro-negra do escalonador CFS, mesma estrutura que o CFS real do Linux
usa). Instale com:

```
pip install -r requirements.txt
```

Para rodar a simulação:

```
python "memoria_versãofinal_agoravai.py" entrada_ES.txt
```

O primeiro argumento é o arquivo de entrada, no formato descrito abaixo.

# Instruções do trabalho 
> É exatamente igual ao que tá no ava

Entrada e Saída (E/S) é uma parte fundamental da operação de sistemas computacionais. Uma das atribuições do sistema operacional (SO) é abstrair e gerenciar o uso dos dispositivos de E/S pelos processos. Neste trabalho, você deverá estender o código do seu escalonador (considerando apenas um algoritmo de escalonamento e um de memória) para incorporar um gerenciador de E/S. A partir de agora, durante a execução de um processo, este pode solicitar a realização de operações de E/S de um dos dispositivos presentes no sistema.

Para este trabalho, será fornecido um arquivo de entrada no seguinte formato.

algoritmoDeEscalonamento|fraçãoDeCPU|políticaMemória|tamanhoMemória|tamanhoPáginasMolduras|percentualAlocação **|numDispositivosES
idDispositivo|numUsosSimultaneos|tempoOperação**
...
tempoCriação|PID|tempoDeExecução|prioridade (ou bilhetes)|qtdeMemoria|sequênciaAcessoPaginasProcesso|**chanceRequisitarES**
...
 
onde:
- **numDispositivosES** representa a quantidade de dispositivos de E/S que o sistema possui
- **idDispositivo** é o identificador do dispositivo de E/S
- **numUsosSimultaneos** representa a quantidade de processos que podem fazer uso daquele dispositivo de forma simultânea
- **tempoOperação** indica quanto tempo o dispositivo demora para executar uma operação de E/S
- **chanceRequisitarES** informa a chance que o processo tem de requisitar uma operação de E/S durante a sua fração de CPU
 
*o arquivo pode conter informações sobre múltiplos dispositivos, um em cada linha
**o arquivo contém informações sobre múltiplos processos, um em cada linha
***Demais atributos conforme especificado em etapas anteriores do trabalho

A cada vez que for trocar o processo em execução na CPU, o seu programa deverá exibir o estado dos processos. Isto é, indicar o processo que está em execução, o(s) processo(s) em estado pronto e o(s) processo(s) bloqueado(s). Para todos, deve ser informado o tempo de CPU restante necessário para a conclusão. Para os processos em estado bloqueado, também deverá ser informado o dispositivo que está sendo utilizado ou aguardado. Além disso, o seu programa deverá mostrar a lista de dispositivos existentes, o seu estado e os processos que estão fazendo uso ou aguardando para fazer uso.

Toda vez que um processo for escolhido para execução na CPU, você deverá determinar, com base na probabilidade informada, se ele solicitará uma operação de E/S naquele ciclo. Caso o processo solicite uma operação de E/S, você também deverá determinar aleatoriamente **qual dispositivo** será solicitado para uso e **em que momento** da fatia isso ocorrerá. Observe que os dispositivos possuem um limite de processos que podem utilizá-los simultaneamente. Caso o processo escolha utilizar um dispositivo que já está em uso por outro processo, este deverá entrar em uma "fila de espera" do dispositivo. Enquanto o processo estiver realizando uma operação de E/S ou aguardando para iniciar uma operação de E/S, ele não poderá ser escalonado para a CPU. Nota-se, porém, que, havendo outros processos em estado "pronto", estes devem prosseguir com a execução normalmente, de acordo com a política de escalonamento.

Ao final da execução, o seu algoritmo deverá mostrar quanto tempo um processo demorou para ser executado, isto é, desde o momento em que foi criado até o momento em que foi concluído. Também deve informar o tempo em que esteve em pronto e o tempo em que esteve em estado bloqueado.

**O que entregar?** Arquivo compactado contendo o código documentado e as instruções de uso. Nomear o arquivo com o seguinte padrão NMatric1_NMatric2_NMatric3_NMatric4.formato (exemplo: 39133_40123_50213_99999.tar.gz). Somente um do grupo precisa entregar!

Avaliação será dividida em três partes:

**Demonstração no laboratório (1,5 ponto):** o código atende à especificação? Os resultados produzidos estão corretos?
**Documentação (0,2 ponto):** o código está bem documentado e possui documentação de uso?
**Conhecimento individual da solução (1,8 ponto):** os/as integrantes do grupo demonstram conhecimento do código desenvolvido?

**Observação:** Em caso de cópia/plágio de código, a nota do trabalho de todos/todas será zerada, independentemente de quem efetivamente fez e de quem copiou. Lembrem, discutir como resolver o problema é permitido, não pode copiar a solução.
