import random
import other_bots
import traders
import run_experiments
import plot_simulation
import numpy

class MyBot(traders.Trader):
    name = 'my_bot'
    
    def simulation_params(self, timesteps,
                          possible_jump_locations,
                          single_jump_probability):
        """Receive information about the simulation."""
        # Number of trading opportunities
        self.timesteps = timesteps
        # A list of timesteps when there could be a jump
        self.possible_jump_locations = possible_jump_locations
        # For each of the possible jump locations, the probability of
        # actually jumping at that point. Jumps are normally
        # distributed with mean 0 and standard deviation 0.2.
        self.single_jump_probability = single_jump_probability
        # A place to store the information we get
        self.information = []
        
        # yao
        # Setting a belief at the beginning
        self.belief = 50.0
        self.alpha = 0.95
        self.start_block_size = 20
        self.min_block_size = 1
        self.sigma = 0.2
        
        self.trades = []
        self.previous_trades_num = 0
        self.max_shares = 10 * self.start_block_size
       
        self.share = 0
        
        self.max_bought_per_round = 5
        self.max_sold_per_round = 5
        
        self.max_trading_volume = 0
        
        # underpricing, long, neutral, short, underpricing
        self.position = 'neutral'
    
    def new_information(self, info, time):
        """Get information about the underlying market value.
        
        info: 1 with probability equal to the current
          underlying market value, and 0 otherwise.
        time: The current timestep for the experiment. It
          matches up with possible_jump_locations. It will
          be between 0 and self.timesteps - 1."""
        self.information.append(info)
        
        #set deviate to 0 if the market price deviates from the true value
        if info == 1:
            self.belief = self.belief
            self.deviate = False
        elif info == 0:
            self.belief = self.belief
            self.deviate = True
            
            
    def trades_history(self, trades, time):
        """A list of everyone's trades, in the following format:
        [(execution_price, 'buy' or 'sell', quantity,
          previous_market_belief), ...]
        Note that this isn't just new trades; it's all of them."""
        
        self.trades = trades
        
        num_new_trades = len(trades) - self.previous_trades_num
        new_trades = trades[-(num_new_trades+1):-1]
        num_bought = 0
        overall_bought_value = 0
        num_sold = 0
        overall_sold_value = 0
        average_bought_price = 0
        average_sold_price = 0
        
        # check which side is dominating
        for this_trade in new_trades:
            if this_trade[1] == 'buy':
                num_bought += this_trade[2]
                overall_bought_value += this_trade[0] * this_trade[2]
            else:
                num_sold += this_trade[2]
                overall_sold_value += this_trade[0] * this_trade[2]
                
        # keep track of maximum trading volume
        current_volume = num_bought + num_sold
        if (self.max_trading_volume < current_volume):
            self.max_trading_volume = current_volume
        
        
        if num_bought != 0:
            average_bought_price = overall_bought_value / num_bought
        if num_sold != 0:
            average_sold_price = overall_sold_value / num_sold

        # if long side is dominating, we raise our belief
        if num_bought > 1.5 * num_sold:
            # we have to compare the current volume with the max volume
            # if the current volume is fairly large and we are dominated by the long side
            # this can be a signal of underpricing
            if current_volume > 0.8 * self.max_trading_volume:
                if self.belief * (2 - self.alpha) < average_bought_price:               
                    self.belief = max((average_bought_price + self.belief)/2, self.belief * (2 - self.alpha))
                self.position = 'underpricing'
            elif current_volume > 0.6 * self.max_trading_volume:
                if self.belief * (2 - self.alpha) < average_bought_price:               
                    self.belief = min((average_bought_price + self.belief)/2, self.belief * (2 - self.alpha))
                self.position = 'long'
            else:
                self.position = 'neutral'    
        # if short side is dominating, we lower our belief
        elif num_sold > 1.5 * num_bought:
            # we have to compare the current volume with the max volume
            # if the current volume is fairly large and we are dominated by the short side
            # this can be a signal of overpricing       
            if current_volume > 0.8 * self.max_trading_volume:
                if self.belief * self.alpha > average_sold_price:               
                    self.belief = min((average_bought_price + self.belief)/2, self.belief * self.alpha)
                self.position = 'overpricing'
            elif current_volume > 0.6 * self.max_trading_volume:
                if self.belief * self.alpha > average_sold_price:                    
                    self.belief = max((average_bought_price + self.belief)/2, self.belief * self.alpha)
                self.position = 'short'
            else:
                self.position = 'neutral'   
        else:
            self.position = 'neutral'
                    
        self.previous_trades_num = len(trades);
       
        # print ('time {}, position {}'.format(time,self.position))
        
    def trading_opportunity(self, cash_callback, shares_callback,
                            check_callback, execute_callback,
                            market_belief):
        """Called when the bot has an opportunity to trade.
        
        cash_callback(): How much cash the bot has right now.
        shares_callback(): How many shares the bot owns.
        check_callback(buysell, quantity): Returns the per-share
          price of buying or selling the given quantity.
        execute_callback(buysell, quantity): Buy or sell the given
          quantity of shares.
        market_belief: The market maker's current belief.

        Note that a bot can always buy and sell: the bot will borrow
        shares or cash automatically.
        """
        
        
        #some on spot adjustment
        
        #adjust if the market price deviates from the true value
        if (self.position == 'long' or self.position == 'underpricing'
            and self.deviate == True):
            self.belief += (1 - self.alpha) * self.belief
        elif (self.position == 'short' or self.position == 'overpricing'
            and self.deviate == True):
            self.belief -= (1 - self.alpha) * self.belief
        
        #if the market_belief has a wide gap from our own spectation, 
        #we are going to compromise by adjusting our belief
        if (abs(market_belief - self.belief) > (1 - self.alpha) * self.belief):
            #scale up our belief
            if (market_belief > self.belief and self.position == 'long'):
                self.belief += (1 - self.alpha / 2) * self.belief
            elif (market_belief > self.belief and self.position == 'underpricing'):
                self.belief += (1 - self.alpha) * self.belief
            #scale down our belief
            elif (market_belief < self.belief and self.position == 'short'):
                self.belief -= (1 - self.alpha / 2) * self.belief
            elif (market_belief < self.belief and self.position == 'overpricing'):
                self.belief -= (1 - self.alpha / 2) * self.belief
            
        
        current_belief = (self.belief + market_belief) / 2.0
        current_belief = max(min(current_belief, 99.0), 1.0)
                
        num_bought = 0
        num_sold = 0
        block_size = self.start_block_size
        
        #repeated buy or sell (can only either buy or sell at one timestamp) 
        #stop buying if it is hitting the upper bound of the maximum amount of shares one can hold (5 * start_block_size)
        while True:
            if (num_bought < self.max_bought_per_round 
                and (check_callback('buy', block_size)< current_belief) 
                    and num_sold == 0
                        and self.share + block_size < self.max_shares):
                execute_callback('buy',block_size)
                self.share += block_size
                num_bought += 1
            elif (num_sold < self.max_sold_per_round
                and num_bought == 0
                    and (check_callback('sell',block_size) > current_belief)):
                execute_callback('sell',block_size)
                self.share -= block_size
                num_sold += 1
            else:
                if block_size == self.min_block_size:
                    break
                block_size = block_size // 2
                if block_size < self.min_block_size:
                    block_size = self.min_block_size
        # reset our belief to align with the current_belief
        self.belief = current_belief
    
    ###### the commented part is just a copy of the fundamental trader
    # def simulation_params(self, timesteps,
    #                       possible_jump_locations,
    #                       single_jump_probability,
    #                       start_belief=50.0,
    #                       alpha=0.9,
    #                       min_block_size=2,
    #                       start_block_size=20):
    #     self.timesteps = timesteps
    #     self.possible_jump_locations = possible_jump_locations
    #     self.single_jump_probability = single_jump_probability
    #     self.belief = start_belief
    #     self.alpha = alpha
    #     self.min_block_size = min_block_size
    #     self.start_block_size = start_block_size
    
    # def new_information(self, info, time):
    #     self.belief = (self.belief * self.alpha
    #                    + info * 100 * (1 - self.alpha))

    # def trades_history(self, trades, time):
    #     self.trades = trades

    # def trading_opportunity(self, cash_callback, shares_callback,
    #                         check_callback, execute_callback,
    #                         market_belief):
    #     current_belief = (self.belief + market_belief) / 2.0
    #     current_belief = max(min(current_belief, 99.0), 1.0)
    #     bought_once = False
    #     sold_once = False
    #     block_size = self.start_block_size
    #     while True:
    #         if (not sold_once
    #             and (check_callback('buy', block_size)
    #                  < current_belief)):
    #             execute_callback('buy', block_size)
    #             bought_once = True
    #         elif (not bought_once
    #               and (check_callback('sell', block_size)
    #                    > current_belief)):
    #             execute_callback('sell', block_size)
    #             sold_once = True
    #         else:
    #             if block_size == self.min_block_size:
    #                 break
    #             block_size = block_size // 2
    #             if block_size < self.min_block_size:
    #                 block_size = self.min_block_size
        
        
                
def main():
    bots = [MyBot()]
    fundamental = 10
    technical = 1
    bots.extend(other_bots.get_bots(fundamental,technical))
    print ('Fundamental: {}, Technical: {}'.format(fundamental,technical))
    # Plot a single run. Useful for debugging and visualizing your
    # bot's performance. Also prints the bot's final profit, but this
    # will be very noisy.
    #plot_simulation.run(bots, 200, lmsr_b=250)
    
    # Calculate statistics over many runs. Provides the mean and
    # standard deviation of your bot's profit.
    run_experiments.run(bots, num_processes=2, simulations=2000, lmsr_b=250)

# Extra parameters to plot_simulation.run:
#   timesteps=100, lmsr_b=150

# Extra parameters to run_experiments.run:
#   timesteps=100, num_processes=2, simulations=2000, lmsr_b=150

# Descriptions of extra parameters:
# timesteps: The number of trading rounds in each simulation.
# lmsr_b: LMSR's B parameter. Higher means prices change less,
#           and the market maker can lose more money.
# num_processes: In general, set this to the number of cores on your
#                  machine to get maximum performance.
# simulations: The number of simulations to run.

if __name__ == '__main__': # If this file is run directly
    main()
