# Portfolio Weighting

cc-liquid uses rank power position sizing to control how capital is distributed across positions. By adjusting a single `rank_power` parameter, you can range from equal weighting (all positions same size) to heavy concentration in your highest-conviction positions.

## Visual Overview

### Example schemes impact on position sizing

![Portfolio Weighting Grid](assets/weighting_schemes_grid.png)

The grid above shows how three different weighting schemes distribute capital across long and short positions in various portfolio configurations. Notice how rank power creates concentration in top-ranked positions while maintaining the target leverage.

### Concentration Effects

![Concentration Curves](assets/concentration_curves.png)

These curves demonstrate how the rank power parameter controls concentration:

- **Power = 0.0** (equal weight, default): All positions get the same allocation
- **Power = 0.5-1.0**: Mild concentration favoring top positions  
- **Power = 1.5-2.0**: Moderate concentration
- **Power = 3.0+**: Heavy concentration in top few positions

## Configuration

### YAML Configuration

```yaml
portfolio:
  num_long: 60
  num_short: 50
  target_leverage: 4.0
  rank_power: 0.0  # 0.0 = equal weight (default), higher = more concentration
```

### CLI Override

```bash
# Equal weight (default)
cc-liquid analyze --set portfolio.rank_power=0.0

# Moderate concentration
cc-liquid analyze --set portfolio.rank_power=1.5

# Heavy concentration for live trading
cc-liquid rebalance --set portfolio.rank_power=2.0
```

## How Rank Power Works

Positions are weighted using the formula `(rank/n)^power`, where:

- `rank` is the position's rank within its side (1 = best)
- `n` is the total number of positions on that side
- `power` is your concentration parameter

**Key insight:** When `power = 0.0`, the formula `(rank/n)^0 = 1.0` for all ranks, producing equal weighting. As you increase power, top-ranked positions (stronger signals) receive progressively more capital.

### Examples

```yaml
# Equal weighting (default)
rank_power: 0.0

# Mild concentration
rank_power: 0.5

# Moderate concentration
rank_power: 1.5

# Heavy concentration
rank_power: 2.5
```
