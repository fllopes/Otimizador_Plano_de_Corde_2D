# 🪚 Otimizador de Cortes 2D para Marcenaria

Um otimizador de plano de corte vetorial desenvolvido em Python para marcenaria (MDF, Compensado, Madeira Maciça) e vidraçaria. O algoritmo utiliza empacotamento *Binary Tree (Shortest-Axis-Split)* com simulação de Monte Carlo para encontrar o melhor aproveitamento de chapas brutas ou retalhos.

São necessários dois arquivos de entrada no formato CSV:
* Lista de peças que compõe o projeto (lista de corte),
* Lista de peças disponíveis como matéria prima (lista de matéria prima).

---

## 🚀 Como Executar

Este projeto foi construído **100% com bibliotecas nativas do Python**. Não é necessário instalar nenhum pacote via `pip`.

1. Baixe o arquivo `otimizador.py` e os seus arquivos `.csv` para a mesma pasta.
2. Certifique-se de ter o [Python 3.7 ou superior](https://www.python.org/) instalado.
3. Abra o terminal na pasta e execute:
   ```bash
   python otimizador.py

O programa solicitará os caminhos dos arquivos CSV de entrada, a estratégia de otimização e a profundidade de cálculo. Ao final, gera um relatório visual completo em HTML com desenhos vetoriais (SVG).

## Modos de Otimização e Profundidade

Ao iniciar o programa, você poderá escolher a estratégia de cálculo adequada para o seu projeto:

1. Estratégia de Otimização
(D) Otimização Dupla [PADRÃO]: Prioriza em 1º lugar o menor custo financeiro total (R$). Em caso de empate entre layouts de mesmo valor, seleciona o que gera menor desperdício de área (m²). É a opção recomendada para a maioria dos casos.

(G) Otimização Geométrica: Ignora os preços das chapas e foca 100% em minimizar o espaço restante e o número total de chapas utilizadas. Ideal para materiais com custo por m² uniforme.

(F) Otimização Financeira: Foca estritamente no menor valor final em R$, sem considerar o desperdício geométrico residual.

2. Profundidade de Cálculo (Iterações)
(1) Rápido (100 iterações): Otimização em ~0.1s. Recomendado para testes rápidos de medidas.

(2) Padrão (2.000 iterações) [PADRÃO]: Equilíbrio ideal entre tempo (~1.0s) e qualidade de encaixe para projetos de até 50 peças.

(3) Profundo (10.000 iterações): Busca exaustiva (~3.0s) recomendada para projetos grandes ou com amplo inventário de retalhos.

## Formatação dos Arquivos CSV de Entrada

Os arquivos de entrada devem utilizar ponto e vírgula (;) como separador. Os nomes dos cabeçalhos devem estar na Linha 1 (a ordem das colunas é livre).

Linhas Comentadas (//)
Você pode desativar temporariamente qualquer linha de peças ou chapas sem precisar apagá-la: basta iniciar a linha com //.Exemplo: //1;500;300;15;Telhado_pq;1,3;;Não será ignorada pelo otimizador.

Arquivo 1: Matérias-Primas (Chapas Brutas e Retalhos)

Cabeçalho,Tipo,Descrição
id,Texto / Int,"Identificador único da chapa (ex: 1, CHAPA-A)"
Comprimento,Inteiro,Medida em mm (ex: 2750)
Largura,Inteiro,Medida em mm (ex: 1830)
Profundidade,Inteiro,Espessura em mm (ex: 15)
Materia_prima,Texto,"Descrição do material (ex: MDF Branco, Teca)"
custo_unidade,Decimal,"Preço unitário da chapa (ex: 150.00 ou 150,00)"
largura_corte,Inteiro,(Opcional) Espessura da serra/kerf em mm (Padrão: 3)
Qtd,Inteiro,(Opcional) Limite de estoque disponível (Padrão: Infinito)

Exemplo de CSV (materias_primas.csv):
id;Comprimento;Largura;Profundidade;Materia_prima;largura_corte;custo_unidade;Qtd
1;1600;800;25;Teca;4;638.19;
//2;1600;800;19;Teca;4;425.43;
3;1200;800;19;Teca;4;372.23;
4;1600;600;19;Teca;4;372.23;

Arquivo 2: Lista de Corte (Peças do Projeto)

Cabeçalho,Tipo,Descrição
Quantidade,Inteiro,Número de peças idênticas (ex: 4)
Comprimento,Inteiro,Medida final em mm (ex: 780)
Largura,Inteiro,Medida final em mm (ex: 100)
Profundidade,Inteiro,Espessura da peça em mm (ex: 15)
Função,Texto,Nome/Identificação da peça (ex: Lateral Gaveta)
Material,Texto,"ID(s) das chapas permitidas, separados por vírgula (ex: 1,3)"
Girar,Texto,Sim (permite rotação 90º) ou Não

Colunas Opcionais — Fita de Borda (Edge Banding)

Se utilizar fitas de borda, inclua as colunas abaixo. O script descontará automaticamente a espessura da fita nas bordas marcadas com x:

espessura da fita: Espessura da fita aplicada em mm (ex: 1 ou 2).

fita_c1, fita_c2: Marque x nas bordas que receberão fita ao longo do comprimento.

fita_l1, fita_l2: Marque x nas bordas que receberão fita ao longo da largura.

Exemplo de CSV (lista_corte.csv):

Quantidade;Comprimento;Largura;Profundidade;Função;Material;Complemento;Girar;espessura da fita;fita_c1;fita_c2;fita_l1;fita_l2
1;513;304;19;Porta;3,4,5,6,7,8;;Não;1;x;x;;
//1;500;304;19;Porta menor;3,4,5,6,7,8;;Não;1;;;x;x
2;487;30;19;Vista;3,4,5,6,7,8;;Não;0;;;;

## Relatório Gerado

Ao finalizar a execução, o programa salva automaticamente um relatório HTML no mesmo diretório dos arquivos de entrada, informando o caminho completo no terminal. O relatório inclui:

Resumo financeiro e lista de compras com custos unitários, subtotais por chapa, modo utilizado e custo total estimado do projeto.

Mapa visual interativo (SVG) para cada chapa utilizada, exibindo o posicionamento de cada peça, rotações e dimensões exatas de corte.

## Autor

Desenvolvido por Filipe Lopes
Contato: fllopes@gmail.com

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo LICENSE para mais detalhes.
