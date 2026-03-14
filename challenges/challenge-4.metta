;; ----------------------------------------------------------
;; CHALLENGE 4: Family Tree Knowledge Base (KB)
;; ----------------------------------------------------------
;; DATA:
;; Use the following atoms as your ground truth:
;; (Male Chandler) (Female Monica) (Male John) (Female Pam)
;; (Parents (Monica Chandler) John) (Parent John Bob)
;;
;; TASK:
;; Write queries or functions using 'match' to retrieve 
;; specific relationships.
;;
;; GOALS:
;; 1. Get the Parents of John.
;; 2. Get the Mother of Pam.
;; 3. Get the Siblings of Pam (Hard: must share parents but not be Pam).
;; 4. Get all Predecessors of Bob (Recursive search).
