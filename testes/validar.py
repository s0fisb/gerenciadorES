"""
Verificador automático do gerenciador de E/S.

Roda o simulador (memoria_versãofinal_agoravai.py) várias vezes contra cada
arquivo de entrada em testes/ (mais entrada_ES.txt na raiz), sem alterar o
código do simulador, e confere invariantes do enunciado a partir da saída
padrão (formato em painel, um bloco por troca real de processo na CPU):

  1. Sai com código 0, sem traceback em stderr.
  2. Todo PID da entrada aparece na linha final de resumo.
  3. total == pronto + bloqueado + tempoDeExecução (do arquivo de entrada).
  4. total, pronto, bloqueado >= 0 e total >= tempoDeExecução.
  5. Em todo painel, len(usando) <= numUsosSimultaneos do dispositivo.
  6. 'esperando' só é não-vazia quando 'usando' está na capacidade máxima.
  7. Um PID nunca aparece em Executando/Prontos/Bloqueados em mais de um
     desses papéis no mesmo painel.
  8. Todo PID em Bloqueados aparece em usando/esperando do dispositivo
     indicado naquele mesmo painel (e o dispositivo existe).
  9. O tempo restante impresso por PID nunca aumenta ao longo da execução.
 10. O relógio (t=X do título do painel) nunca regride.
 11. O rótulo de estado do dispositivo (livre/parcialmente ocupado/ocupado)
     bate com usando/capacidade.
 12. A linha final de memória "fifo|lru|nuf|opt|melhor" existe e é bem formada.

Uso:
    python testes/validar.py [N_REPETICOES]

N_REPETICOES (padrão 15) é quantas vezes cada arquivo é executado — não há
semente fixa no simulador, então repetir aumenta a chance de bater em casos
de fila de espera, CPU ociosa etc.
"""
import glob
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RAIZ, "memoria_versãofinal_agoravai.py")

RE_TITULO = re.compile(r"^─+ t=(\d+) — P(\d+) assume a CPU ─+$")
RE_EXEC = re.compile(r"^Executando : P(\d+) \(restante=(-?\d+)\)$")
RE_PRONTOS = re.compile(r"^Prontos    : (.*)$")
RE_BLOQUEADOS = re.compile(r"^Bloqueados : (.*)$")
RE_ITEM_PRONTO = re.compile(r"P(\d+)\(restante=(-?\d+)\)")
RE_ITEM_BLOQUEADO = re.compile(r"P(\d+)\(restante=(-?\d+), (\S+)\)")
RE_DISPOSITIVO = re.compile(
    r"^\s*(\S+) \[(.+?)\]\s+usando=\[(.*?)\]\s+esperando=\[(.*?)\]$"
)
RE_RESUMO = re.compile(
    r"^P(\d+): total=(-?\d+) pronto=(-?\d+) bloqueado=(-?\d+)$"
)
RE_MEMORIA = re.compile(r"^-?\d+\|-?\d+\|-?\d+\|-?\d+\|(FIFO|LRU|NUF|empate)$")


def ler_entrada(caminho):
    with open(caminho, "r") as f:
        linhas = [l.strip() for l in f if l.strip()]
    cfg = linhas[0].split("|")
    num_dispositivos = int(cfg[6])

    dispositivos = {}
    idx = 1
    for _ in range(num_dispositivos):
        partes = linhas[idx].split("|")
        dispositivos[partes[0].strip()] = int(partes[1])
        idx += 1

    processos = {}
    for linha in linhas[idx:]:
        p = linha.split("|")
        pid = int(p[1])
        processos[pid] = int(p[2])  # tempoDeExecução

    return dispositivos, processos


def parse_pids(texto):
    """'P1, P2' -> [1, 2]; '' -> []."""
    texto = texto.strip()
    if not texto:
        return []
    return [int(item.strip().lstrip("P")) for item in texto.split(",")]


def validar_execucao(caminho_entrada, saida, dispositivos, processos, erros):
    pids_pendentes = set(processos)
    ultimo_restante = {}  # pid -> última quantidade de "restante" vista
    ultimo_tempo = -1
    linhas = saida.splitlines()
    n = len(linhas)
    i = 0

    def erro(msg):
        erros.append(f"[{caminho_entrada}] linha {i}: {msg}")

    def checar_restante(pid, restante, rotulo):
        prev = ultimo_restante.get(pid)
        if prev is not None and restante > prev:
            erro(f"P{pid} ({rotulo}) restante aumentou ({prev} -> {restante})")
        ultimo_restante[pid] = restante

    while i < n:
        m_tit = RE_TITULO.match(linhas[i])
        if not m_tit:
            i += 1
            continue

        tempo_titulo, pid_titulo = int(m_tit.group(1)), int(m_tit.group(2))
        if tempo_titulo < ultimo_tempo:
            erro(f"relógio regrediu ({ultimo_tempo} -> {tempo_titulo})")
        ultimo_tempo = tempo_titulo
        i += 1

        m_exec = RE_EXEC.match(linhas[i]) if i < n else None
        if not m_exec:
            erro("esperava linha 'Executando' após o título")
            continue
        pid_exec, restante_exec = int(m_exec.group(1)), int(m_exec.group(2))
        if pid_exec != pid_titulo:
            erro(f"título diz P{pid_titulo} mas Executando diz P{pid_exec}")
        checar_restante(pid_exec, restante_exec, "executando")
        i += 1

        m_pr = RE_PRONTOS.match(linhas[i]) if i < n else None
        if not m_pr:
            erro("esperava linha 'Prontos' após 'Executando'")
            continue
        prontos_pids = set()
        for pid_s, rest_s in RE_ITEM_PRONTO.findall(m_pr.group(1)):
            pid, rest = int(pid_s), int(rest_s)
            prontos_pids.add(pid)
            checar_restante(pid, rest, "pronto")
        i += 1

        m_bl = RE_BLOQUEADOS.match(linhas[i]) if i < n else None
        if not m_bl:
            erro("esperava linha 'Bloqueados' após 'Prontos'")
            continue
        bloqueados_pids = set()
        dispositivo_do_pid = {}
        for pid_s, rest_s, disp in RE_ITEM_BLOQUEADO.findall(m_bl.group(1)):
            pid, rest = int(pid_s), int(rest_s)
            bloqueados_pids.add(pid)
            dispositivo_do_pid[pid] = disp
            checar_restante(pid, rest, "bloqueado")
            if disp not in dispositivos:
                erro(f"P{pid} bloqueado em dispositivo inexistente {disp!r}")
        i += 1

        if prontos_pids & bloqueados_pids:
            erro(f"PID(s) {prontos_pids & bloqueados_pids} em Prontos e Bloqueados ao mesmo tempo")
        if pid_exec in prontos_pids or pid_exec in bloqueados_pids:
            erro(f"P{pid_exec} está executando e também listado em Prontos/Bloqueados")

        if i < n and linhas[i] == "":
            i += 1
        if i >= n or linhas[i] != "Dispositivos:":
            erro("esperava linha 'Dispositivos:'")
            continue
        i += 1

        vistos_em_dispositivo = {}
        while i < n:
            md = RE_DISPOSITIVO.match(linhas[i])
            if not md:
                break
            nome, estado, usando_txt, esperando_txt = md.groups()
            usando = parse_pids(usando_txt)
            esperando = parse_pids(esperando_txt)
            cap = dispositivos.get(nome)
            if cap is None:
                erro(f"dispositivo {nome!r} não está na entrada")
            elif len(usando) > cap:
                erro(f"dispositivo {nome} com {len(usando)} em uso > capacidade {cap}")
            if esperando and cap is not None and len(usando) < cap:
                erro(f"dispositivo {nome} tem fila de espera com vaga livre (usando={usando}, cap={cap})")
            if cap is None:
                estado_esperado = estado
            elif not usando:
                estado_esperado = "livre"
            elif len(usando) < cap:
                estado_esperado = "parcialmente ocupado"
            else:
                estado_esperado = "ocupado"
            if estado != estado_esperado:
                erro(f"dispositivo {nome} diz estado={estado} mas usando={usando} (esperado {estado_esperado!r})")
            for pid in usando + esperando:
                vistos_em_dispositivo[pid] = nome
            i += 1

        for pid, disp in dispositivo_do_pid.items():
            if vistos_em_dispositivo.get(pid) != disp:
                erro(
                    f"P{pid} diz estar em {disp!r} mas não aparece em usando/esperando "
                    f"desse dispositivo (achou {vistos_em_dispositivo.get(pid)!r})"
                )

    # resumo final
    achou_memoria = False
    for i, linha in enumerate(linhas):
        m = RE_RESUMO.match(linha)
        if m:
            pid, total, pronto, bloqueado = (int(x) for x in m.groups())
            pids_pendentes.discard(pid)
            exec_time = processos.get(pid)
            if exec_time is None:
                erros.append(f"[{caminho_entrada}] linha {i}: P{pid} não está na entrada")
                continue
            if total < 0 or pronto < 0 or bloqueado < 0:
                erros.append(f"[{caminho_entrada}] linha {i}: valor negativo em P{pid}")
            if total != pronto + bloqueado + exec_time:
                erros.append(
                    f"[{caminho_entrada}] linha {i}: P{pid} total={total} != "
                    f"pronto({pronto})+bloqueado({bloqueado})+exec({exec_time})"
                )
            if total < exec_time:
                erros.append(
                    f"[{caminho_entrada}] linha {i}: P{pid} total({total}) < "
                    f"tempoDeExecução({exec_time})"
                )
        elif RE_MEMORIA.match(linha):
            achou_memoria = True

    if pids_pendentes:
        erros.append(
            f"[{caminho_entrada}] processo(s) {pids_pendentes} nunca apareceram "
            f"no resumo final"
        )
    if not achou_memoria:
        erros.append(f"[{caminho_entrada}] linha de resultado de memória ausente/malformada")


def rodar(caminho_entrada, repeticoes):
    dispositivos, processos = ler_entrada(caminho_entrada)
    erros_totais = []

    for rep in range(repeticoes):
        resultado = subprocess.run(
            [sys.executable, SCRIPT, caminho_entrada],
            cwd=RAIZ, capture_output=True, text=True, timeout=60,
        )
        if resultado.returncode != 0:
            trecho = "\n".join(resultado.stderr.strip().splitlines()[-8:])
            erros_totais.append(
                f"[{caminho_entrada}] repetição {rep}: saiu com código "
                f"{resultado.returncode}\n{trecho}"
            )
            continue

        erros_rep = []
        validar_execucao(caminho_entrada, resultado.stdout, dispositivos, processos, erros_rep)
        if erros_rep:
            erros_totais.append(f"--- repetição {rep} ---")
            erros_totais.extend(erros_rep)

    return erros_totais


def main():
    repeticoes = int(sys.argv[1]) if len(sys.argv) > 1 else 15

    arquivos = sorted(glob.glob(os.path.join(RAIZ, "testes", "*.txt")))
    entrada_es = os.path.join(RAIZ, "entrada_ES.txt")
    if os.path.exists(entrada_es):
        arquivos.append(entrada_es)

    if not arquivos:
        print("Nenhum arquivo de entrada encontrado.")
        sys.exit(1)

    tudo_ok = True
    for caminho in arquivos:
        nome = os.path.relpath(caminho, RAIZ)
        erros = rodar(caminho, repeticoes)
        if erros:
            tudo_ok = False
            print(f"FALHOU  {nome}  ({len(erros)} problema(s) em {repeticoes} repetições)")
            for e in erros:
                print(f"    {e}")
        else:
            print(f"OK      {nome}  ({repeticoes} repetições)")

    print()
    print("TUDO OK" if tudo_ok else "HÁ FALHAS ACIMA")
    sys.exit(0 if tudo_ok else 1)


if __name__ == "__main__":
    main()
