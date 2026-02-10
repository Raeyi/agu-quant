# Feature/Signal 字段中英文映射

说明：这是当前代码中常见字段的中英文对照与含义，方便理解输出结果。

## 基础行情字段

| 字段 | 中文含义 |
| --- | --- |
| date | 交易日期 |
| symbol | 标准化代码（如 000001.SZ） |
| code | 纯数字代码（如 000001） |
| name | 名称 |
| exchange | 交易所（SZ/SH/BJ） |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| prev_close | 前收盘价 |
| volume | 成交量 |
| amount | 成交额 |
| pct_chg | 涨跌幅（百分比） |
| amplitude | 振幅（百分比） |
| turnover | 换手率（百分比） |
| adj_method | 复权方式 |

## 涨跌停/情绪相关

| 字段 | 中文含义 |
| --- | --- |
| limit_up | 涨停标记（1/0） |
| limit_down | 跌停标记（1/0） |
| high_pct | 最高价涨幅 |
| low_pct | 最低价涨幅 |
| broken_limit_up | 炸板标记（触及涨停后回落） |
| consecutive | 连板数 |
| first_limit_up | 首板数量 |
| second_limit_up | 二板数量 |
| third_plus_limit_up | 三板及以上数量 |
| promotion_rate | 连板晋级率（次日二板/首板） |
| limit_up_ratio | 涨停占比 |
| limit_down_ratio | 跌停占比 |
| broken_ratio | 炸板率 |
| max_consecutive | 当日最大连板高度 |
| total | 当日样本总数 |
| up | 上涨数量 |
| down | 下跌数量 |
| flat | 平盘数量 |
| broken | 炸板数量 |

## 题材/主题面板

| 字段 | 中文含义 |
| --- | --- |
| theme | 题材/板块名称 |
| avg_pct_chg | 平均涨跌幅 |

## 龙虎榜与营业部（资金/席位）

| 字段 | 中文含义 |
| --- | --- |
| inst_buy | 机构买入额 |
| inst_sell | 机构卖出额 |
| inst_net | 机构净买入 |
| broker | 营业部名称 |
| buy | 买入额 |
| sell | 卖出额 |
| net | 净买入 |
| buy_count | 买入个股数 |
| sell_count | 卖出个股数 |
| stocks | 买入股票列表（字符串） |
| rows | 记录条数 |
| code_count | 涉及股票数 |
| broker_count | 涉及营业部数 |
| active_days | 活跃天数 |
| avg_net | 日均净买入 |
| avg_turnover | 日均买卖额（buy+sell） |
| buy_ratio | 买入占比（buy/(buy+sell)） |

注意：该模块里的 `turnover` 表示买卖总额（buy+sell），与行情里的换手率含义不同。

## 技术标准化

| 字段 | 中文含义 |
| --- | --- |
| turnover_z | 换手率 Z 分数 |
| turnover_norm | 换手率归一化（0-1） |
| turnover_pct_rank | 换手率滚动分位 |
| orderbook_strength | 封单强度（买一/卖一占比） |
| orderbook_imbalance | 封单差异（买一-卖一占比） |
| orderbook_z | 封单强度 Z 分数 |
| orderbook_norm | 封单强度归一化（0-1） |

## 关键形态识别

| 字段 | 中文含义 |
| --- | --- |
| breakout_volume | 放量突破 |
| turnover_board | 换手板（涨停且换手率高） |
| one_word_board | 一字板 |
| shrink_volume_board | 缩量板（涨停且量能偏低） |

## 评分与候选池

| 字段 | 中文含义 |
| --- | --- |
| score | 评分 |
| suggested_position | 建议仓位 |
| reason | 评分理由 |
| ret_3d | 近 3 日收益 |
| ret_10d | 近 10 日收益 |
| avg_amount_5d | 近 5 日平均成交额 |
| vol_5d | 近 5 日波动幅度 |
| drawdown_10d | 近 10 日回撤 |
| base_score | 基础分 |
| min_score | 最低分 |
| max_score | 最高分 |
| w_amount_high | 高成交额权重 |
| w_amount_low | 低成交额权重 |
| w_drawdown_deep | 深回撤权重 |
| w_vol_high | 高波动权重 |

## 回测与组合

| 字段 | 中文含义 |
| --- | --- |
| equity | 资金曲线 |
| net_ret | 净收益 |
| pos | 当前仓位 |
| pos_prev | 前一日仓位 |
| entry_date | 进场日期 |
| exit_date | 出场日期 |
| win_rate | 胜率 |
| avg_win | 平均盈利 |
| avg_loss | 平均亏损 |
| profit_factor | 盈亏比 |
| avg_hold_days | 平均持仓天数 |
