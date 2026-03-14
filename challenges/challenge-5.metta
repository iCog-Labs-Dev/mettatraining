;; ----------------------------------------------------------
;; CHALLENGE 5: Python Interoperability (py-atom)
;; ----------------------------------------------------------
;; TASK:
;; MeTTa is designed to leverage Python's vast libraries. 
;; Use the 'py-atom' tool for the following tasks:
;;
;; 1. The Mathematician: Access 'math.pow' from Python to 
;;    calculate 2 to the power of 10.
;; 2. Real-World OS Inquiry: Access 'os.cpu_count' to 
;;    detect the hardware specs of your current machine.
;; 3. Data Cleaning: Query a MeTTa space for duplicates 
;;    and use Python sets/list-comprehension to return 
;;    only unique entries.
;;
;; HINT:
;; You will need to use (bind! math (py-atom math))
