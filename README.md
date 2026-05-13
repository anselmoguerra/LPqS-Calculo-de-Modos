[README.md](https://github.com/user-attachments/files/27710874/README.md)
# LPqS-Calculo-de-Modos
cálculo de modos de ondas estacionárias em salas retangulares
# Calculadora de Modos de Sala

## DOI: https://doi.org/10.5281/zenodo.20159898

Esta pasta contém uma versão em Python da planilha `MODOS2026.xlsm`. A ferramenta calcula os modos acústicos de uma sala retangular, separa os modos em axiais, tangenciais e oblíquos, exporta tabelas em CSV e gera gráficos para análise em aula.

O objetivo didático é ajudar estudantes de música a enxergar por que algumas salas reforçam ou cancelam certas notas graves. Em baixas frequências, a sala não se comporta como um campo sonoro uniforme: ela tem ressonâncias. Essas ressonâncias são os modos.

## Aplicação HTML

Também há uma versão interativa que roda direto no navegador, sem servidor:

```text
index.html
styles.css
app.js
```

Abra `index.html` no navegador. A aplicação permite alterar dimensões, recalcular os modos em tempo real, ver gráficos dinâmicos, ler avisos acústicos e exportar `modes.csv`.

## Como Rodar em Python

Use Python 3 com `matplotlib` instalado. A partir desta pasta:

```bash
python3 room_modes.py \
  --length 5.2 \
  --width 7.1 \
  --height 3.1 \
  --temperature 24
```

Argumentos principais:

| Argumento | Significado |
| --- | --- |
| `--length` ou `-l` | Comprimento da sala em metros. |
| `--width` ou `-w` | Largura da sala em metros. |
| `--height` ou `-H` | Altura da sala em metros. |
| `--temperature` ou `-t` | Temperatura do ar em graus Celsius. O padrão é `24`. |
| `--max-frequency` ou `-f` | Frequência máxima analisada. O padrão é `300 Hz`. |
| `--output-dir` ou `-o` | Pasta onde os CSVs e PNGs serão salvos. |

## Exemplos Prontos

Também é possível usar exemplos embutidos:

```bash
python3 room_modes.py --example small --output-dir outputs/sala_pequena
```

```bash
python3 room_modes.py --example studio --output-dir outputs/estudio
```

```bash
python3 room_modes.py \
  --example concert \
  --max-frequency 160 \
  --output-dir outputs/sala_concerto
```

Dimensões usadas nos exemplos:

| Exemplo | Dimensões | Uso didático |
| --- | --- | --- |
| `small` | `3.0 x 3.6 x 2.4 m` | Sala pequena, próxima de proporções simples. Boa para observar problemas no grave. |
| `studio` | `5.2 x 7.1 x 3.1 m` | Sala de estúdio com proporções mais espalhadas. |
| `concert` | `18.0 x 28.0 x 11.0 m` | Sala grande. Use `--max-frequency 160` para gráficos menos carregados. |

## Arquivos Gerados

| Arquivo | Conteúdo |
| --- | --- |
| `modes.csv` | Lista de todos os modos: índices `p`, `q`, `r`, frequência, frequência arredondada e classificação. |
| `summary.csv` | Dimensões, velocidade do som, volume, área, proporção normalizada e contagem de modos. |
| `bands.csv` | Quantidade de modos por banda de frequência e densidade modal. |
| `warnings.txt` | Avisos sobre proporções problemáticas da sala. |
| `acoustic_recommendations.txt` | Relatório didático em português com faixas críticas, efeitos audíveis prováveis, estratégias de tratamento e cautelas de medição. |
| `modal_plot.png` | Contagem de modos por frequência arredondada, separada por tipo. |
| `modal_distribution.png` | Distribuição dos modos individuais no eixo de frequência. |
| `modes_by_band.png` | Modos por banda, empilhados por tipo. |
| `modal_density.png` | Densidade modal por banda. |

## Fórmulas Usadas

Velocidade do som:

```text
c = 20.06 * sqrt(T + 273)
```

`T` é a temperatura em graus Celsius.

Frequência modal de uma sala retangular:

```text
f = c/2 * sqrt((p/L)^2 + (q/W)^2 + (r/H)^2)
```

Onde:

| Símbolo | Significado |
| --- | --- |
| `L` | Comprimento da sala, em metros. |
| `W` | Largura da sala, em metros. |
| `H` | Altura da sala, em metros. |
| `p`, `q`, `r` | Índices inteiros do modo. Eles não podem ser todos zero. |

Classificação dos modos:

| Tipo | Regra | Como imaginar |
| --- | --- | --- |
| Axial | Só um índice é diferente de zero. | Energia entre duas paredes opostas. Geralmente é o tipo mais forte. |
| Tangencial | Dois índices são diferentes de zero. | Energia envolvendo quatro superfícies. |
| Oblíquo | Três índices são diferentes de zero. | Energia envolvendo as seis superfícies. |

Outras grandezas:

```text
volume = L * W * H
area = 2 * (L*W + L*H + W*H)
frequencia_rotulada_como_schroeder_na_planilha = 3 * c / min(L, W, H)
```

A última expressão mantém a saída da planilha original. Ela é útil para comparação com o arquivo Excel, mas está nomeada com cuidado no CSV porque a fórmula usada pela planilha é `3c / menor dimensão`.

## Como Ler os Gráficos

No gráfico `modal_distribution.png`, cada ponto é uma ressonância da sala. Se muitos pontos aparecem muito próximos em uma região grave, aquela faixa tende a ficar mais problemática: algumas notas podem soar exageradas, longas ou mal definidas.

No gráfico `modal_plot.png`, picos altos indicam frequências onde vários modos caem no mesmo número de hertz. Isso é um sinal de atenção, principalmente quando envolve modos axiais.

No gráfico `modes_by_band.png`, uma distribuição mais gradual é geralmente mais desejável do que bandas vazias seguidas por bandas muito carregadas.

No gráfico `modal_density.png`, a densidade modal ponderada tende a aumentar com a frequência. Para aproximar o comportamento da planilha original, modos axiais entram com peso `1`, tangenciais com `0.5` e oblíquos com `0.25`; depois o total ponderado é dividido pelo centro da banda. Em salas pequenas, a região grave costuma ter poucos modos separados, por isso é a parte mais sensível para projeto, tratamento e posicionamento de caixas e ouvintes.

## Avisos de Proporção

O arquivo `warnings.txt` aponta problemas simples:

- dimensões quase iguais;
- proporções perto de `2:1` ou `3:1`;
- modos axiais coincidentes;
- primeiros modos axiais muito próximos;
- proporção normalizada pouco espalhada.

Esses avisos não substituem projeto acústico completo. Eles servem como triagem didática: ajudam a perceber quando a geometria da sala já favorece acúmulos de energia em certas frequências.

## Relatório de Recomendações

O arquivo `acoustic_recommendations.txt` expande os avisos em uma leitura acústica didática. Ele procura:

- agrupamentos de modos;
- frequências repetidas ou quase repetidas;
- modos axiais fortes;
- acúmulo de baixa frequência;
- lacunas na distribuição modal;
- proporções problemáticas da sala.

As recomendações são hipóteses de trabalho, não prescrições definitivas. O relatório sempre deve ser conferido com medições reais, como sweep senoidal, resposta ao impulso e análise de RT/EDT, porque a resposta muda muito com a posição das caixas, dos microfones e dos ouvintes.

## Observação Sobre a Planilha

A planilha original gera grades de modos e usa fatores de compensação para reduzir a influência dos modos tangenciais e oblíquos na densidade modal. Esta versão enumera diretamente combinações únicas `(p, q, r)` para a tabela de modos, mas aplica pesos apenas no cálculo do gráfico de densidade modal ponderada.

Conteúdo didático, metodologia acústica, textos e documentação:
Creative Commons Attribution 4.0 International (CC BY 4.0)

https://creativecommons.org/licenses/by/4.0/

## Licença

Código-fonte:
MIT License

Conteúdo didático e documentação:
CC BY 4.0

Autor:
Anselmo Guerra – LPqS / EM / UFG

