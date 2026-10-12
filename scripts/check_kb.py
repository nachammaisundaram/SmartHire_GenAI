from src import adapters as a

for q in ["What should a fresher learn first for Gen AI?", "Should I do a Ph.D. after MCA?"]:
    print("\nQ:", q)
    for i, t in enumerate(a.kb_search(q, 3), 1):
        print(i, t[:90].replace("\n", " "))
