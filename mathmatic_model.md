变量
|变量|含义|
|-|-|
|$m$|机器数量，i|
|$n$|工件数量，j|
|$pro_{ji}$|工件i在机器j上的加工时间|
|$P$|加工序列集合，其中$P$|
|$$||

决策变量
|决策变量|含义|
|-|-|
|$\lambda_{ip}$|加工序列p在机器i上加工，$i \in \{1,2,...,m\}, p \in P$|
|$offset_{i}$|机器i，$offset_{i} \ge 0$|
|$s_{ij}$|机器i上加工工件j的开始时间，$s_{ij} \ge 0$|
|$f_{ij}$|机器i上加工工件j的结束时间，$f_{ij} \ge 0$|
|$c$|最大加工时间|



约束：
1. 每个机器加工分配一个加工序列($\alpha_i$)
$\sum_{p}{\lambda_{ip}} == 1, \forall i$

2. 在机器i上加工工件j的开始时间被确定为在模式p中的工件j的开始时间 ($\gamma_{ij}$) starting time on machine i for job j is determined by the starting time of job j in the selected pattern p
$\sum_{p}{P_{ip0j} * \lambda_{ip}} + offset_{i} - s_{ij} = 0, \forall i, j$

3. 同理结束时间约束如下($\gamma_{ij}$)
$\sum_{p}{P_{ip1j} * \lambda_{ip}} + offset_{i} - f_{ij} = 0, \forall i, j$
   
4. 内部机器约束()
$f_{ij} <= s_{i + 1, j}>, \forall i \in \{1,2,...,m -  1\}, j$

5. 开始完成时间
$s_{ij} + pro_{ji} == f_{ij}, \forall i, j$

6. 加工时间约束
$c \ge f_{m-1, j}, \forall j$



定价子问题
变量
|变量|含义|
|-|-|
|$i$|机器编号，i|

决策变量
|决策变量|含义|
|-|-|
|$s_{j}$|加工工件j的开始时间，$0 \ge s_{j} \ge 100$|
|$f_{j}$|加工工件j的结束时间，$0 f_{j} \ge 100$|
|$x_{kj}$|工件k是否在j前加工，$0 x_{kj} \in \{0, 1\}$|

1. 工件j的加工时间
$s_{j} + pro_{ji} = f_{j}, \forall j$

2. 工件k和j的顺序
$x_{jk} + x_{kj} = 0, \forall j, k \in {1,2,...,n}, j \ne k$

3. 如果加工j -> k，那么j的开始时间为0
$s_{j} \le 50 * ((n - 1) - \sum_{k}{x_{jk}}), \forall j, k \in {1,2,...,n}$

4. 如果在机器i上先做k再做j，那么开始结束时间连续
$f_{k} <= s_{j} + M * (1 - x_{kj}), \forall j, k$



分支策略






# 函数
|函数名称|解释|场景|||
|-|-|-|-|-|
|addConsNode|Add a constraint to the given node||||
|consactive|sets activation notification method of constraint handler||||
|repropagateNode|marks the given node to be propagated again the next time a node of its subtree is processed||||
|addConsNode|||||
|addConsNode|||||
|addConsNode|||||