---
layout: default
title: Ethereum Futures Signal Strategy
---

# Sentient.ai

Welcome to Sentient.ai—where cutting-edge artificial intelligence meets the power of decentralized finance on the Sui blockchain.

At Sentient.ai, we've reimagined trading by combining advanced AI agents with robust quantitative strategies. Simply deposit your funds into our secure vault, and let our intelligent system execute precision trades on your behalf. Our platform is designed for both seasoned traders and newcomers, offering a transparent, efficient, and automated trading experience that adapts in real-time to market dynamics.

## Table of Contents

- [Overview](#overview)
- [Agent Introduction](#agent-introduction)
- [Strategy Details](#strategy-details)
- [Modeling Approach](#modeling-approach)
- [Technical Background](#technical-background)
- [Backtest Performance](#backtest-performance)
- [Installation and Usage](#installation-and-usage)
- [License](#license)

## Overview

This repository contains the implementation of a proprietary signal-based trading strategy designed to trade Ethereum futures. The strategy leverages advanced machine learning techniques to generate trading signals (long, short, or neutral) based on historical market data. Although the precise target label remains proprietary, the model uses an adapted version of the triple barrier labeling method to capture price dynamics. The signal generation is based on a sophisticated feature engineering process combined with a gradient boosting model (using LightGBM). As a result, the strategy is designed to forecast trading signals for Ethereum futures. By framing the problem as a multi-class classification task, the model determines whether to take a **long**, **short**, or **neutral** position. 

> **Note:**  
> For proprietary reasons, the specific target label (the class the model is predicting) is not disclosed. However, the labeling process is based on an adapted  > triple barrier method. It should be noted that for the purposes of keeping our model confidential and the backend such as the feature generation, model training, and all the other code, we have decided not to publish it due to the confidentiality of our strategy.



## Strategy Details

- **Market:** Ethereum futures  
- **Signal Types:** Long, Short, Neutral  
- **Labeling Method:** An adapted version of the triple barrier labeling method  
- **Backtest Results:** Out-of-sample backtests (October 2024 – January 2025) have generated returns in excess of 50%. This is based on the best performing insample parameter from Jan 2023 - June 2024.

### Triple Barrier Labeling

The triple barrier method uses three barriers to define the outcome of a trade: an upper barrier, a lower barrier, and a time barrier. In our adaptation, the label \(L\) is determined as follows:

$$
L =
\begin{cases}
1 & \text{if } P_t \geq P_0 (1 + \theta) \\
-1 & \text{if } P_t \leq P_0 (1 - \theta) \\
0 & \text{otherwise, or if the time barrier is reached}
\end{cases}
$$

Where:  
- $P_0$ is the initial price,  
- $P_t$ is the price at time \(t\),  
- $\theta$ is a threshold percentage.

Where:  
- $P_0$ is the initial price,  
- $P_t$ is the price at time $t$,  
- $\theta$ is a threshold percentage.



## Modeling Approach

The prediction problem is framed as a **classification task** where the model predicts one of three actions:
- **Long:** Initiate or maintain a bullish position.
- **Short:** Initiate or maintain a bearish position.
- **Neutral:** Stay out of the market.

We use **LightGBM**, a powerful gradient boosting framework, to build our model. Gradient boosting iteratively improves predictions by minimizing a loss function.

### Gradient Boosting with LightGBM

The LightGBM model builds an additive model of weak learners (decision trees). At each iteration $m$, the model is updated as:

$$
F_m(x) = F_{m-1}(x) + \nu \cdot h_m(x)
$$

Where:
- $F_m(x)$ is the model prediction after $m$ iterations,
- $h_m(x)$ is the new weak learner added at iteration $m$,
- $\nu$ is the learning rate.

#### Loss Function

The multi-class log-loss function, which the model minimizes, is given by:

$$
\mathcal{L} = -\sum_{i=1}^{N} \sum_{k=1}^{K} y_{i,k} \log(p_{i,k})
$$

Where:
- $y_{i,k}$ is an indicator (0 or 1) of whether sample $i$ belongs to class $k$,
- $p_{i,k}$ is the predicted probability for class $k$.

#### Regularization

LightGBM applies regularization to prevent overfitting:

$$
\Omega(f) = \gamma T + \frac{1}{2} \lambda \sum_{j=1}^{T} w_j^2
$$

Where:
- $T$ is the number of leaves in the tree,
- $w_j$ are the leaf weights,
- $\gamma$ and $\lambda$ are regularization parameters.

## Backtest Performance

Out-of-sample backtests conducted from **October 2024 to January 2025** have shown promising results, with cumulative returns exceeding **50%**. These results underscore the robustness of the model in varying market conditions.
