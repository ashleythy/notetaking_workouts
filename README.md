# Initial thoughts

1. 2025-10-24: 
- the aim is to create some sort of an app where i can write down notes wrt exercises i'm doing (specifically in an unstructured, free-form format) and the app should ideally be able to log (and track) the exercises (and whatever details i've put down such as number of reps, duration etc) in a structured, organized way
- for e.g.
    - input into app (unstructured):
        - "did 30 squats. tired"
        - "push ups. 3x10"
    - output (structured):
        - "exercise 1: squats. reps: 30. feeling: tired"
        - "exercise 2: push ups. reps: 10. sets: 3. feeling: NaN"
- an input upon entering the app could be a single exercise. an input could also be a combination of various exercises and its corresponding descriptions 
- core components:
    - frontend (ui):
        - enter notes
        - view logs
    - backend (api):
        - accept notes in writing
        - pre and postprocess notes
        - store notes
    - database 
        - store notes
    - nlp layer / engine 
        - performs logic to convert unstructured to structured text
        - performs any other downstream analysis such as summarisation, insights etc 

2. 2025-10-26:
- expected output of the nlp layer / engine:
    - identify entities from text statement. key entities:
        - exercise type
        - number of sets 
        - number of reps 
        - feeling 
        - performance 
        - etc 