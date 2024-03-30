import pandas as pd
import numpy as np
import statsmodels.api as sm
# import statsmodels.graphics.tsaplots as tsa
import matplotlib.pyplot as plt
from plot_settings import *

def lower_tail_dependence_index_matrix(X, alpha=0.05):
    """
    Calculate the lower tail dependence index matrix using the empirical
    approach.

    Parameters
    ----------
    X : ndarray
        Returns series of shape n_sample x n_features.
    alpha : float, optional
        Significance level for lower tail dependence index.
        The default is 0.05.

    Returns
    -------
    corr : ndarray
        The lower tail dependence index matrix of shape n_features x
        n_features.

    Raises
    ------
    ValueError
        When the value cannot be calculated.
    """
    if not (0 < alpha < 1):
        raise ValueError("Alpha must be between 0 and 1.")

    if isinstance(X, pd.DataFrame):
        cols = X.columns.tolist()
        X1 = X.to_numpy()
    else:
        X1 = X.copy()

    m, n = X1.shape
    k = np.int32(np.ceil(m * alpha))
    mat = np.ones((n, n))

    if k > 0:
        sorted_X = np.sort(X1, axis=0)

        for i in range(n):
            for j in range(i + 1, n):
                u = sorted_X[k - 1, i]
                v = sorted_X[k - 1, j]
                ltd = np.sum(np.where((X1[:, i] <= u) & (X1[:, j] <= v), 1, 0)) / k

                mat[i, j] = ltd
                mat[j, i] = mat[i, j]

            u = sorted_X[k - 1, i]
            v = sorted_X[k - 1, i]
            ltd = np.sum(np.where((X1[:, i] <= u) & (X1[:, i] <= v), 1, 0)) / k

            mat[i, i] = ltd

    mat = np.clip(np.round(mat, 8), a_min=1.0e-8, a_max=1)

    if isinstance(X, pd.DataFrame):
        mat = pd.DataFrame(mat, index=cols, columns=cols)
    
    return mat

def convert_cov_or_corr(matrix, cov2corr=True):
    r"""
    Generate a correlation matrix from a covariance matrix cov or vise versa.

    Parameters
    ----------
    cov : ndarray
        Covariance matrix of shape n_features x n_features, where
        n_features is the number of features.

    Returns
    -------
    corr : ndarray
        A correlation matrix.

    Raises
    ------
        ValueError when the value cannot be calculated.

    """

    if cov2corr:
        flag = False
        if isinstance(matrix, pd.DataFrame):
            cols = matrix.columns.tolist()
            flag = True

        cov1 = np.array(matrix, ndmin=2)
        std = np.sqrt(np.diag(cov1))
        corr = np.clip(cov1 / np.outer(std, std), a_min=-1.0, a_max=1.0)

        if flag:
            corr = pd.DataFrame(corr, index=cols, columns=cols)
        return corr
    
    else:
        flag = False
        if isinstance(matrix, pd.DataFrame):
            cols = matrix.columns.tolist()
            flag = True

        cov = matrix * np.outer(std, std)

        if flag:
            cov = pd.DataFrame(cov, index=cols, columns=cols)
        return cov

def stationaryBootstrap(data: np.ndarray, m, sampleLength)-> np.ndarray:
    """
    Returns a bootstraped sample of the time-series "data" of length "sampleLength. 
    The algorithm used is stationary bootstrap from 1994 Politis & Romano.
    
    Args:     
        data ... ndarray array. A single vector of numbers containing the time-series.
        m    ... floating number. Parameter to stationary bootstrap indicating the average length of each block in the sample.
        sampleLength ... integer. Length of the bootstrapped sample returned as output.
    
    Returns:     
        sample ... ndarray array containing the final bootstraped sample.
    
    Example of use:
    >>> import numpy as np
    >>> data = np.array([1,2,3,4,5,6,7,8,9,10])
    >>> m = 4
    >>> sampleLength = 12
    >>> StationaryBootstrap(data, m, sampleLength)
    Out[0]:  array([[9.],
                    [3.],
                    [4.],
                    [5.],
                    [6.],
                    [7.],
                    [8.],
                    [7.],
                    [2.],
                    [3.],
                    [4.],
                    [2.]])

    Original paper about stationary bootstrap:
    Dimitris N. Politis & Joseph P. Romano (1994) The Stationary Bootstrap, Journal of the American Statistical 
        Association, 89:428, 1303-1313, DOI: 10.1080/01621459.1994.10476870    

    Implemented by Gregor Fabjan from Qnity Consultants on 12/11/2021.
    """
    
    accept = 1/m
    lenData = data.shape[0]
    if sampleLength is None:
        sampleLength = lenData

    sampleIndex = np.random.randint(0,high=lenData,size=1)
    sample = np.zeros((sampleLength,1))
    for iSample in range(sampleLength):
        if np.random.uniform(0,1,1)>=accept:
            sampleIndex += 1
            if sampleIndex >= lenData:
                sampleIndex=0        
        else:
            sampleIndex = np.random.randint(0,high = lenData,size=1)

        sample[iSample,0] = data[sampleIndex]
    return sample.ravel()

def win_rate(signals, returns, trade_spread=False):
    sigs = signals[1:-1].values.ravel()
    rets = (returns).shift(1).dropna().values.ravel()
    tps = np.where((np.abs(sigs) == 1) & (rets > 0), 1, 0)
    
    if trade_spread:
        in_trade = np.where(np.abs(sigs) == 1, True, np.nan)
        win_rate = sum(tps)/len(in_trade[~np.isnan(in_trade)])
    else:
        win_rate = sum(tps)/len(sigs)
        
    return win_rate

def subset_data(df:pd.DataFrame, train_split_func:bool=False, test_size:float=0.25, subset_count:int=2, sorted=False) -> tuple:
    """ Split dataframe into train test split or the number of chosen subsets."""
    if train_split_func:
        from sklearn.model_selection import train_test_split
        X_train, X_test, _, _ = train_test_split(df, df, test_size=test_size, shuffle=False)
        return (X_train, X_test)
    else:
        import math 
        chunk_size = math.ceil(len(df) / subset_count)
        chunks = []
        for i in range(subset_count):
            chunks.append(df[i*chunk_size:(i+1)*chunk_size])
        # train = pd.DataFrame(index=df.index)
        # cols = chunks[0].columns
        # for i in range(len(chunks)):
        #     for j in cols:
        #         # print(i, j)
        #         train[f'{j}_set-{i+1}'] = chunks[i][j]
        # if sorted:
        #     return train.reindex(sorted(train.columns), axis=1)
        # else:
        #     return train
        return chunks

def plot_cumulative_return(returns):
    if not isinstance(returns, pd.DataFrame):
        raise ValueError("Returns must be a DataFrame")
    cumret_df = (1+returns).cumprod()
    linestyles = ['-', '--', '-.', ':']  # List of different linestyles
    linewidths = [3, 2, 3, 2, 3]
    for index, i in enumerate(cumret_df.columns):
        cumret_df[i].plot(label=i, linewidth=linewidths[index % (len(linewidths))],  linestyle=linestyles[index % len(linestyles)])
    plt.legend()
    plt.title("Cumulative Return")
    plt.show()
    
def plot_correlation_heatmap(returns, dividers=['.','-U']):
    if not isinstance(returns, pd.DataFrame):
        raise ValueError("Returns must be a DataFrame")
    tmpret = returns.copy()
    from seaborn import heatmap
    # Calculate correlation matrix
    cols = [col.split(dividers[0])[0] for col in tmpret.columns]
    cols = [col.split(dividers[1])[0] for col in cols]
    tmpret.columns = cols
    correlation_matrix = tmpret.corr()
    # Create a mask to display only the bottom-left diagonal
    mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
    # Set up the matplotlib figure
    plt.figure(figsize=(10, 8))
    # Choose a different color palette
    cmap = 'viridis'
    # Create a heatmap using seaborn
    ax = heatmap(correlation_matrix, annot=True, cmap=cmap, fmt=".2f", linewidths=.5, mask=mask)
    # Get the current figure
    fig = plt.gcf()
    # Set the title of the plot
    plt.title('Correlation Heatmap of Returns', fontsize=16)
    # Increase the font size of the annotations
    plt.xticks(fontsize=12, rotation=-20)
    plt.yticks(fontsize=12)
    # Set a background color for the heatmap
    plt.gca().set_facecolor('lightgray')
    # Remove the x-label
    plt.xlabel('')
    # Show the plot
    plt.show()

def plot_EMA_volatility(returns, span=36, frequency=None, return_emas=False):
    if not isinstance(returns, pd.DataFrame):
        raise ValueError("Returns must be a DataFrame")
    if frequency is None:
        raise ValueError('enter frequency')
    emas = returns.ewm(span=span).std()*np.sqrt(frequency)
    linestyles = ['-', '--', '-.', ':']  # List of different linestyles
    linewidths = [2, 3, 3, 3, 3]
    for index, code in enumerate(returns.columns):
        emas[code].plot(label=f'{code}', linewidth=linewidths[index % (len(linewidths))],  linestyle=linestyles[index % len(linestyles)])
    plt.title(f'Exponential Rolling Volatility Span {span}')
    plt.ylabel('Volatility')
    plt.legend()
    plt.show()
    if return_emas:
        return emas     

def plot_rolling_correlations(returns, span=36, portfolio=None, return_corrs=False, raw=False):
    if not isinstance(returns, pd.DataFrame):
        raise ValueError("Returns must be a DataFrame")
    if portfolio is None:
        raise ValueError('enter bmk')
    if raw:
        sma = returns.rolling(window=span).corr()[portfolio]
    #      ema = returns.ewm(span=span).corr()[portfolio]
    else:
        sma = returns.dropna().rolling(window=span).corr()[portfolio].dropna()
    #      ema = returns.ewm(span=span).corr().dropna()[skip:][portfolio]

    grouped_pairs = {}
    # Iterate over the multi-index pairs
    for pair in sma.index:
        second_value = pair[1]
        if second_value not in grouped_pairs:
            grouped_pairs[second_value] = []
        grouped_pairs[second_value].append(pair)
    
    # dates = [str(i[0]).split(" ")[0] for i in grouped_pairs[portfolio]]
    unique_headings = returns.drop(portfolio,axis=1).columns
    linestyles = ['-', '--', '-.', ':']  # List of different linestyles
    linewidths = [2, 3, 3, 3, 3]
    rollingCorrs = {}
    for index, i in enumerate(unique_headings):
        rollingCorr = sma.loc[grouped_pairs[i]].reset_index(drop=True)
        rollingCorr.index = returns.loc[grouped_pairs[i][0][0]:].index
        rollingCorr.plot(label=i, linewidth=linewidths[index % (len(linewidths))],  linestyle=linestyles[index % len(linestyles)])
        rollingCorrs[i] = rollingCorr
    plt.ylabel('Correlations')
    plt.xlabel('Date')
    # xticks = range(0, len(dates), int((len(dates)/self.annualiser)/2))
    # xtick_labels = [dates[i] for i in xticks]
    # plt.xticks(xticks, xtick_labels, rotation=-45)
    plt.title(f'Rolling Correlation to {portfolio} - Span: {span}')
    plt.legend()
    plt.show()
    if return_corrs:
        return pd.DataFrame().from_dict(rollingCorrs)