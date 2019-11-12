# %%
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cvxpy as cp


# %%
df = pd.read_csv("SP500.csv")
df.drop(['Unnamed: 0'], axis = 1, inplace=True)
print(df.shape)
ticker = list(df.columns)[1:]
# rebalance portfolio every month (20 trading days)

INITIAL_BALANCE = 24628
TRANS_COST = 0.00
# define the risk-free rate
RISKFREE = 1.02


# %%
def PriceReverse(df, cycle, time):
    """ Compute 1M Price Reversal as the following:
        PM_{i,t} = (Close_{i,t} - Close_{i, t-1}) / Close_{i, t-1}
        Order: Ascending
    Argument df: dataframe object (n*1 vector)
            cycle: how many days to look back to see its reversal
            time: current index for df to look at
    """
    try:
        previous_price = df.iloc[time - cycle]
        return (df.iloc[time] - previous_price) / previous_price
    except KeyError:
        return None

def Price_High_Low(df, cycle, time):
    """
    Compute High-minus-low:
    HL_{i,t} = (High_{i,t} - Close_{i,t}) / (Close_{i,t} - Low_{i,t})
    Order: Descending
    Argument df: dataframe object (n*1 vector)
            cycle: how many days to look back to see its reversal
            time: current index for df to look at
    """
    try:
        High = max(df.iloc[time-cycle:time])
        Low = min(df.iloc[time-cycle:time])
        return -(High - df.iloc[time]) / (df.iloc[time] - Low)
    except KeyError:
        return None

def Vol_Coefficient(df, cycle, time):
    """
    Compute Coefficient of Variation:
    CV_{i,t} = Std(Close_i, cycle) / Ave(Close_i, cycle)
    Order: Descending
        Argument df: dataframe object (n*1 vector)
            cycle: how many days to look back to see its reversal
            time: current index for df to look at
    """
    try:
        std = np.std(df.iloc[time-cycle:time])
        avg = np.mean(df.iloc[time-cycle:time])
        return -std / avg
    except KeyError:
        return None

def AnnVol(df, cycle, time):
    """
    Compute Coefficient of Variation:
    AnnVol = sqrt(252) * sqrt(1/21 * sum(r_{i,t-j}^2))
    where r_{i,s} = log(Close_{i,t} / Close_{i,t-1})
    Order: Descending
        Argument df: dataframe object (n*1 vector)
            cycle: how many days to look back to see its reversal
            time: current index for df to look at
    """
    try:
        r_2 = int(0)
        for i in range(1, cycle):
            log = np.log(df.iloc[time-i] / df.iloc[time-i-1])
            r_2 += log**2
        result = np.sqrt(252/cycle * r_2)
        return -result
    except KeyError:
        return None

trading_strategies = [PriceReverse, Price_High_Low, Vol_Coefficient, AnnVol]

# %%
def MinVariance(data, ranking, time, cycle):
    """
    MinVariance minimizes variance (needs short positions)
    Argument ranking: list of stocks from PitchStock
            return weighting for each stock (in percentage)
    """
    covar = np.zeros(shape = (len(ranking), cycle))
    for i in range(len(ranking)):
        covar[i] = data[ranking[i]].iloc[time+1-cycle:time+1]
    inv_cov_matrix = np.linalg.inv(np.cov(covar))
    ita = np.ones(inv_cov_matrix.shape[0])
    weight = (inv_cov_matrix @ ita) / (ita @ inv_cov_matrix @ ita)
    return weight

def EqualWeight(data, ranking, time, cycle):
    """
    EqualWeight assign weight by 1/N
    return weighting for each stock (in percentage)
    """
    N = len(ranking)
    weight = np.ones(shape=N) / N
    return weight

def MeanVariance_Constraint(data, ranking, time, cycle):
    """
    Mean Variance solved by convex optimization
    return weighting for each stock (in percentageg)
    """
    covar = np.zeros(shape = (len(ranking), cycle))
    for i in range(len(ranking)):
        covar[i] = data[ranking[i]].iloc[time+1-cycle:time+1]
    cov_matrix = np.cov(covar)
    weight = cp.Variable(shape = len(ranking))
    objective = cp.Minimize(cp.quad_form(weight, cov_matrix))
    constraints = [cp.sum(weight) == 1, weight >= 1 / (2 * len(ranking))]
    problem = cp.Problem(objective, constraints)
    result = problem.solve()
    return weight.value


def RiskParity(data, ranking, time, cycle):
    """
    RiskParity inversely invest for stock according to their volatility
    disregards covariance is the major drawback
    return weighting for each stock (in percentage)
    """



# %%
class Agent():
    def __init__(self, balance, data, strategies, cycle, max_holding):
        """
        Balance: dictionary (accounting book)
        Max_holding is the maximum number of stocks this agent can hold
        Cycle is the rebalancing period
        Data is the dataset
        Strategies is which factor investing stratgy this Agent has in disposal
        """
        self.balance = balance
        self.data = data
        self.strategies = strategies
        self.cycle = cycle
        self.equity = INITIAL_BALANCE
        self.re = float()
        self.tran_cost = float()
        self.rf = np.power(RISKFREE, self.cycle/252)
        self.max_holding = max_holding


    def PitchStock(self, strategy, time):
        """
        Argument strategy: a function that takes (df, cycle, time) as argument
        return ranking: dictionary {Stock: Value} Value is some metric
        """
        cycle = self.cycle
        data = self.data
        max_holding = self.max_holding
        ranking = {}
        for i in ticker:
            ranking[i] = strategy(data[i], cycle, time)
        result = sorted(ranking, key = ranking.get)[:max_holding]
        return result
        

    def Trading(self, ranking, time):
        """
        Argument ranking: list of stocks
        returns nothing but changes the balance and record of the Agent
        """
        # take all necessary attributes from the class
        cost = 0
        equity = self.equity
        data = self.data
        balance = self.balance
        rf = self.rf
        max_holding = self.max_holding
        avail_cash = balance['cash'] * rf
        # buying
        for i in ranking:
            if i not in balance:
                num_to_buy = (equity / max_holding) // data[i].iloc[time]
                balance[i] = num_to_buy
                change = num_to_buy * data[i].iloc[time]
                cost += num_to_buy * TRANS_COST
                avail_cash -= change

        # selling
        for i in list(balance):
            if i not in ranking and i != 'cash':
                num_to_sell = balance[i]
                del balance[i]
                change = num_to_sell * data[i].iloc[time]
                cost += num_to_sell * TRANS_COST
                avail_cash += change

        # reassign values to the class attributes
        balance['cash'] = avail_cash
        self.balance = balance
        equity = equity + avail_cash - cost
        self.re = equity / INITIAL_BALANCE
        self.equity = equity
        self.tran_cost += cost
        
        
    def BackTesting(self):
        """
        This is backtsting for all strategies
        Return two dictionary
            1. return for each strategy
            2. overall cost for each strategy
        """
        strategies = self.strategies
        print("There are %s strategies we are testing." % len(strategies))
        print("They are: ")
        for i in strategies:
            print("     %s" % i.__name__)
        portfolio_perform = {}
        for strategy in strategies:
            # use BackTesting_Single to get the three value of metrics needed
            total_return, vol, sharpe = self.BackTesting_Single(strategy)
            portfolio_perform[strategy.__name__] = [total_return, vol, sharpe]
            # reset balance, equity, re, and transaction cost for the agent
            self.reset()  
            print("\n")
        # turn this dictionary into a nicely presentable dataframe
        table = pd.DataFrame.from_dict(portfolio_perform, orient='index')
        table.columns = ['Annualized Return', 'Volatility', 'Sharpe Ratio']
        return table
    

    def BackTesting_Single(self, strategy):
        """
        This is backtsting for one single strategy
        Return the total return, volatility and Sharpe ratio
        """
        cycle = self.cycle
        data = self.data
        print("Testing %s" % strategy.__name__)
        T = len(data) // cycle
        print("We are rebalancing for %s number of times." % T)
        portfolio_re = []
        for i in range(1, T):
            time = i * cycle
            ranking = self.PitchStock(strategy, time)
            self.Trading(ranking, time)
            print("Rebalancing for %s time!" % i)
            portfolio_re.append(self.re)
        vol = np.std(portfolio_re)
        total_return = (np.power(self.re, 252 // cycle / T) - 1)*100
        sharpe = (total_return - (RISKFREE - 1)*100) / vol
        return total_return , vol, sharpe

    def reset(self):
        """
        This reset the Agent to its initial holding. 
        Apply this method between testing different strategies.
        """
        self.balance = {'cash': INITIAL_BALANCE}
        self.equity = INITIAL_BALANCE
        self.re = float()
        self.tran_cost = float()
            

# %%


# %%
wsw = Agent({'cash': INITIAL_BALANCE}, df, trading_strategies, 20, 10)

# %%
ranking = wsw.PitchStock(trading_strategies[0], 2000)
wsw.Trading(ranking, 2480)

# %%
wsw.BackTesting()

# %%
wsw.BackTesting_Single(PriceReverse)

# %%