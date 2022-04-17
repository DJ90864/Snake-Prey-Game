
"""
    This program implements one variety of the snake 
    game (https://en.wikipedia.org/wiki/Snake_(video_game_genre))
"""

import threading
import queue        #the thread-safe queue from Python standard library

from tkinter import Tk, Canvas, Button
import random, time

class Gui():
    """
        This class takes care of the game's graphic user interface (gui)
        creation and termination.
    """
    def __init__(self, queue, game):
        """        
            The initializer instantiates the main window and 
            creates the starting icons for the snake and the prey,
            and displays the initial gamer score.
        """
        #some GUI constants
        scoreTextXLocation = 60
        scoreTextYLocation = 15
        textColour = "white"
        #instantiate and create gui
        self.root = Tk()
        self.canvas = Canvas(self.root, width = WINDOW_WIDTH, 
            height = WINDOW_HEIGHT, bg = BACKGROUND_COLOUR)
        self.canvas.pack()
        #create starting game icons for snake and the prey
        self.snakeIcon = self.canvas.create_line(
            (0, 0), (0, 0), fill=ICON_COLOUR, width=SNAKE_ICON_WIDTH)
        self.preyIcon = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=ICON_COLOUR, outline=ICON_COLOUR)
        #display starting score of 0
        self.score = self.canvas.create_text(
            scoreTextXLocation, scoreTextYLocation, fill=textColour, 
            text='Your Score: 0', font=("Helvetica","11","bold"))
        #binding the arrow keys to be able to control the snake
        for key in ("Left", "Right", "Up", "Down"):
            self.root.bind(f"<Key-{key}>", game.whenAnArrowKeyIsPressed)

    def gameOver(self):
        """
            This method is used at the end to display a
            game over button.
        """
        gameOverButton = Button(self.canvas, text="Game Over!", 
            height = 3, width = 10, font=("Helvetica","14","bold"), 
            command=self.root.destroy)
        self.canvas.create_window(200, 100, anchor="nw", window=gameOverButton)
    

class QueueHandler():
    """
        This class implements the queue handler for the game.
    """
    def __init__(self, queue, gui):
        self.queue = queue
        self.gui = gui
        self.queueHandler()
    
    def queueHandler(self):
        '''
            This method handles the queue by constantly retrieving
            tasks from it and accordingly taking the corresponding
            action.
            A task could be: game_over, move, prey, score.
            Each item in the queue is a dictionary whose key is
            the task type (for example, "move") and its value is
            the corresponding task value.
            If the queue.empty exception happens, it schedules 
            to call itself after a short delay.
        '''
        try:
            while True:
                task = self.queue.get_nowait()
                if "game_over" in task:
                    gui.gameOver()
                elif "move" in task:
                    points = [x for point in task["move"] for x in point]
                    gui.canvas.coords(gui.snakeIcon, *points)
                elif "prey" in task:
                    gui.canvas.coords(gui.preyIcon, *task["prey"])
                elif "score" in task:
                    gui.canvas.itemconfigure(
                        gui.score, text=f"Your Score: {task['score']}")
                self.queue.task_done()
        except queue.Empty:
            gui.root.after(100, self.queueHandler)


class Game():
    '''
        This class implements most of the game functionalities.
    '''
    def __init__(self, queue):
        """
           This initializer sets the initial snake coordinate list, movement
           direction, and arranges for the first prey to be created.
        """
        self.queue = queue
        self.score = 0
        #starting length and location of the snake
        #note that it is a list of tuples, each being an
        # (x, y) tuple. Initially its size is 5 tuples.       
        self.snakeCoordinates = [(495, 55), (485, 55), (475, 55),
                                 (465, 55), (455, 55)]
        #initial direction of the snake
        self.direction = "Left"
        self.gameNotOver = True
        self.preyCoordinates = tuple()

        self.createNewPrey()

    def superloop(self) -> None:
        """
            This method implements a main loop
            of the game. It constantly generates "move" 
            tasks to cause the constant movement of the snake.
            Use the SPEED constant to set how often the move tasks
            are generated.
        """
        SPEED = 0.15     #speed of snake updates (sec)
        while self.gameNotOver:
            self.move() #the snake keeps moving if the game is not over.
            time.sleep(SPEED)

    def whenAnArrowKeyIsPressed(self, e) -> None:
        """ 
            This method is bound to the arrow keys
            and is called when one of those is clicked.
            It sets the movement direction based on 
            the key that was pressed by the gamer.
        """
        currentDirection = self.direction
        #ignore invalid keys
        if (currentDirection == "Left" and e.keysym == "Right" or 
            currentDirection == "Right" and e.keysym == "Left" or
            currentDirection == "Up" and e.keysym == "Down" or
            currentDirection == "Down" and e.keysym == "Up"):
            return
        self.direction = e.keysym

    def move(self) -> None:
        """ 
            This method implements what is needed to be done
            for the movement of the snake.
            It generates a new snake coordinate. 
            If based on this new movement, the prey has been 
            captured, it adds a task to the queue for the updated
            score and also creates a new prey.
            It also calls a corresponding method to check if 
            the game should be over. 
            The snake coordinates list (representing its length 
            and position) should be correctly updated.
        """
        NewSnakeCoordinates = self.calculateNewCoordinates()
        x = NewSnakeCoordinates[0]
        y = NewSnakeCoordinates[1]

        #if the prey is within the limits of the snake's head, the prey gets caught.
        PreyCaught = x in range(self.preyCoordinates[0], self.preyCoordinates[2]) and y in range(self.preyCoordinates[1], self.preyCoordinates[3])
        
        if PreyCaught:
            self.score += 1 #increment score
            self.queue.put({"score": self.score}) #add score to print new score
            self.createNewPrey() #add a new prey to the canvas
            self.snakeCoordinates.append(NewSnakeCoordinates) #add another part to the head of the snake.
            self.queue.put({"move": self.snakeCoordinates}) 
        else:
            newCoordinates = self.snakeCoordinates[1:]  #loose the last part of the snake
            newCoordinates.append(NewSnakeCoordinates) #add the new head to the snake
            self.snakeCoordinates = newCoordinates 
            self.queue.put({"move": self.snakeCoordinates})


        self.isGameOver(NewSnakeCoordinates) #check if the game is over incase the snake ran into a wall or bit itself.

    def calculateNewCoordinates(self) -> tuple:
        """
            This method calculates and returns the new 
            coordinates to be added to the snake
            coordinates list based on the movement
            direction and the current coordinate of 
            head of the snake.
            It is used by the move() method.    
        """
        lastX, lastY = self.snakeCoordinates[-1]
        
        #the snake stpes are 10 pixels, so it increases or decreases x and y coordinate according to the direction it's moving. 
        if self.direction == "Left":
            return ( lastX - 10, lastY )  
        elif self.direction == "Right":
            return ( lastX + 10, lastY)
        elif self.direction == "Up":
            return (lastX, lastY - 10)
        elif self.direction == "Down":
            return (lastX, lastY + 10) 

    def isGameOver(self, snakeCoordinates) -> None:
        """
            This method checks if the game is over by 
            checking if now the snake has passed any wall
            or if it has bit itself.
            If that is the case, it updates the gameNotOver 
            field and also adds a "game_over" task to the queue. 
        """
        x, y = snakeCoordinates

        if ( x == 5 and self.direction == "Left"    #if the snake's head reaches x coordinate 5 and is going towards left wall, GAME OVER!
        or   x == WINDOW_WIDTH  - 5 and self.direction == "Right"  #if the snake's head reaches x coordinate 495 and is going towards right wall, GAME OVER!
        or   y == WINDOW_HEIGHT - 5 and self.direction == "Down"  #if the snake's head reaches y coordinate 295 and is going towards Down wall, GAME OVER!
        or   y == 5 and self.direction == "Up"  #if the snake's head reaches y coordinate 5 and is going towards Top wall, GAME OVER!
        or   (x, y) in self.snakeCoordinates[:-1] ):   #if the snakes head coordinates match the snake's any other body coordinates.

            self.gameNotOver = False
            self.queue.put({"game_over": True})


    def createNewPrey(self) -> None:
        """ 
            This methods randomly picks an x and a y as the coordinate 
            of the new prey and uses that to calculate the 
            coordinates (x - 5, y - 5, x + 5, y + 5). 
            It then adds a "prey" task to the queue with the calculated
            rectangle coordinates as its value. This is used by the 
            queue handler to represent the new prey.                    
            To make playing the game easier, set the x and y to be THRESHOLD
            away from the walls. 
        """
        THRESHOLD = 15   #sets how close prey can be to borders

        x = random.randrange(THRESHOLD, WINDOW_WIDTH - THRESHOLD) # x is a random integer between THRESHOLD (left side) and WINDOW_WIDTH - THRESHOLD (right side)
        y = random.randrange(THRESHOLD, WINDOW_HEIGHT - THRESHOLD) # y is a random integer between THRESHOLD (bottom) and WINDOW_WIDTH - THRESHOLD (top)
        
        self.preyCoordinates =  (x - 5, y - 5, x + 5, y + 5) # updating the location of the prey on the canvas
        self.queue.put({"prey": (x - 5, y - 5, x + 5, y + 5)}) # adding a task to the queue to create a new prey


if __name__ == "__main__":
    #some constants for our GUI
    WINDOW_WIDTH = 500           
    WINDOW_HEIGHT = 300 
    SNAKE_ICON_WIDTH = 15
    
    BACKGROUND_COLOUR = "green" 
    ICON_COLOUR = "yellow" 

    gameQueue = queue.Queue()     #instantiate a queue object using python's queue class

    game = Game(gameQueue)        #instantiate the game object

    gui = Gui(gameQueue, game)    #instantiate the game user interface
    
    QueueHandler(gameQueue, gui)  #instantiate our queue handler    
    
    #start a thread with the main loop of the game
    threading.Thread(target = game.superloop, daemon=True).start()

    #start the GUI's own event loop
    gui.root.mainloop()