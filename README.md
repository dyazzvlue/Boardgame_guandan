# GuanDan / 掼蛋

Python 掼蛋引擎，规则见 [rules.md](rules.md)。

## 本地运行

```bash
python main.py --help
```

现有 CLI 入口保持不变。

## 联机模式

将本仓库与 `Boardgame_platform` 同级放置，或设置 `GUANDAN_PATH`。
平台通过独立包 `boardgame_guandan` 加载适配器，内部采用相对导入，
不修改 `sys.path` 或替换其他游戏的模块缓存。游戏仓库与平台插件需一起更新。

`get_state()` 和 `serialize(game)` 默认只返回公开信息；
`get_state_for_player(idx)` 只包含指定玩家自己的手牌，
观战索引 `-1`、无效索引均不含任何玩家手牌。
未初始化的适配器也可以安全请求公开视图。

平台目录的无服务回归入口：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_game_plugins.py
```
