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
        self.alpha = 0.9
        self.start_block_size = 20
        self.min_block_size = 1
        self.sigma = 0.2
        
        self.trades = []
        self.previous_trades_num = 0
        self.max_stock = 10 * self.start_block_size
       
        self.stock = 0
        
        self.max_bought_per_round = 5
        self.max_sold_per_round = 5
        
        # neutral, long, short
        self.position = 'neutral'
    
    def new_information(self, info, time):
        """Get information about the underlying market value.
        
        info: 1 with probability equal to the current
          underlying market value, and 0 otherwise.
        time: The current timestep for the experiment. It
          matches up with possible_jump_locations. It will
          be between 0 and self.timesteps - 1."""
        self.information.append(info)
        
        # yao
        #self.belief = (self.belief * self.alpha 
        #                + info * 100 * (1 - self.alpha))
        adjusted_price = numpy.random.normal(1, self.sigma) * self.belief;
        
        # be more sensitive to the market price change
        #self.belief = (self.belief * self.alpha
        #              + info * 100 * (1 - self.alpha))
        if info == 1:
            self.belief = self.belief
            self.skeptical = False
        elif info == 0:
            self.belief = self.belief
            self.skeptical = True
            
        
            
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
        
        if num_bought != 0:
            average_bought_price = overall_bought_value / num_bought
        if num_sold != 0:
            average_sold_price = overall_sold_value / num_sold
        # print 'bought:{} sold:{}, old_trades: {}, new_trades: {}'.format(num_bought,num_sold,self.previous_trades_num,len(self.trades))
        # if long side is dominating, we raise our belief
        if num_bought > 1.2 * num_sold:
            # as the market price is different from the real price as indicated by the newInfo
            # we are going to be more susceptible to market belief
            if self.skeptical:
                if self.belief * (2 - self.alpha) < average_bought_price:     
                    self.belief = max((average_bought_price + self.belief)/2, self.belief * (2 - self.alpha))
            else:
                if self.belief * (2 - self.alpha) < average_bought_price:               
                    self.belief = min((average_bought_price + self.belief)/2, self.belief * (2 - self.alpha))
            self.position = 'long'
        # if short side is dominating, we lower our belief
        # and we are not skeptical
        elif num_sold > 1.2 * num_bought:
            # as the market price is different from the real price as indicated by the newInfo
            # we are going to be more susceptible to market belief 
            if self.skeptical:
                if self.belief * self.alpha > average_sold_price:     
                    self.belief = min((average_bought_price + self.belief)/2, self.belief * self.alpha)
            else:
                if self.belief * self.alpha > average_sold_price:              
                    self.belief = max((average_bought_price + self.belief)/2, self.belief * self.alpha)
            self.position = 'short'
        else:
            self.position = 'neutral'
                    
        self.previous_trades_num = len(trades);
       
        
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
        # Place a randomly sized trade in the direction of
        # our last information. What could possibly go wrong?
        
        # quantity = random.choice(xrange(1, 100))
        # if (self.information[-1] == 1
        #     and check_callback('buy', quantity) < 99.0):
        #     execute_callback('buy', quantity)
        # elif check_callback('sell', quantity) > 1.0:
        #     execute_callback('sell', quantity)
        
        
        
        #some on spot adjustment
        #if the market_belief has a wide gap from our own spectation, 
        #we are going to compromise by adjusting our belief
        if (abs(market_belief - self.belief) > (1 - self.alpha) * self.belief):
            #scale up our belief
            if (market_belief > self.belief and self.position == 'long'):
                self.belief += (1 - self.alpha) * self.belief
                #self.position = 'long'
            #scale down our belief
            elif (market_belief < self.belief and self.position == 'short'):
                self.belief -= (1 - self.alpha) * self.belief
                #self.position = 'short'
        
        current_belief = (self.belief + market_belief) / 2.0
        current_belief = max(min(current_belief, 99.0), 1.0)
        
        
        # num_bought = 0
        # num_sold = 0
        # block_size = self.start_block_size
        # while True:
        #     if (self.position == 'long' 
        #         and num_bought < self.max_bought_per_round
        #             and (check_callback('buy',block_size) < current_belief)
        #                 and (self.stock + block_size < self.max_stock)):
                                  
        #         execute_callback('buy',block_size)
        #         num_bought += 1
        #         self.stock += block_size
                
        #     elif (self.position == 'short'
        #             and num_sold < self.max_sold_per_round
        #                 and (check_callback('sell',block_size) > current_belief)):
                
        #         execute_callback('sell',block_size)
        #         num_sold += 1
        #         self.stock -= block_size
                
        #     elif (self.position == 'neutral'
        #             and (num_bought < self.max_bought_per_round)
        #                 and (check_callback('buy',block_size) < current_belief)
        #                     and (self.stock + block_size < self.max_stock)):
                            
        #             execute_callback('buy',block_size)
        #             num_bought += 1
        #             self.stock += block_size
                    
        #     elif (self.position == 'neutral'
        #             and (num_sold < self.max_sold_per_round)
        #                 and (check_callback('sell',block_size) > current_belief)):
                        
        #             execute_callback('sell',block_size)
        #             num_bought += 1
        #             self.stock -= block_size
        #     elif (self.position == 'neutral'):
        #         break;
        #     else:
        #         if (block_size == self.min_block_size):
        #             break
        #         block_size = block_size // 2
        #         if (block_size < self.min_block_size):
        #             block_size = self.min_block_sizea
                
        
        
        num_bought = 0
        num_sold = 0
        block_size = self.start_block_size
        while True:
            if (num_bought < self.max_bought_per_round 
                and (check_callback('buy', block_size)< current_belief) 
                    and num_sold == 0
                        and self.stock + block_size < self.max_stock):
                execute_callback('buy',block_size)
                self.stock += block_size
                num_bought += 1
            elif (num_sold < self.max_sold_per_round
                and num_bought == 0
                    and (check_callback('sell',block_size) > current_belief)):
                execute_callback('sell',block_size)
                self.stock -= block_size
                num_sold += 1
            else:
                if block_size == self.min_block_size:
                    break
                block_size = block_size // 2
                if block_size < self.min_block_size:
                    block_size = self.min_block_size
        self.belief = current_belief
        
        
                
def main():
    bots = [MyBot()]
    bots.extend(other_bots.get_bots(10,0))
    # Plot a single run. Useful for debugging and visualizing your
    # bot's performance. Also prints the bot's final profit, but this
    # will be very noisy.
    #plot_simulation.run(bots, 200, lmsr_b=250)
    
    # Calculate statistics over many runs. Provides the mean and
    # standard deviation of your bot's profit.
    run_experiments.run(bots, simulations=2000, lmsr_b=250)

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
