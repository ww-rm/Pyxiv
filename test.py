from config import PyxivConfig

a = PyxivConfig()
a.load("./config.json")
a.save("./config.json")