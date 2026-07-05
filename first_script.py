import requests

response = requests.get("https://pokeapi.co/api/v2/pokemon/pikachu")
data = response.json()

print(data["name"])
print(data["height"])
print(data["weight"])