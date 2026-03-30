function calculateEMA(prices, period) {
    if (prices.length < period) return null;
    const k = 2 / (period + 1);
    // Standard approach: Start with SMA of the first 'period' bars
    let ema = prices.slice(0, period).reduce((acc, val) => acc + val, 0) / period;
    for (let i = period; i < prices.length; i++) {
        ema = (prices[i] - ema) * k + ema;
    }
    return ema;
}
