; ==========================================================
; SHORTEST ROUTE BETWEEN CITIES
; ----------------------------------------------------------
; Self-contained. Load this file and run the queries at the bottom:
;
;   metta bfs-shortest-path.metta
;
; THE PROBLEM
; -----------
; "What is the fewest number of flights from Addis Ababa to Tokyo?"
; Same question a flight search or a maps app answers.
;
; HOW IT WORKS
; ------------
; Search by depth: look for a route of 0 legs, then 1, then 2, and
; so on. The first depth that finds anything gives a SHORTEST route
; -- if a shorter one existed we would already have stopped.
;
; This is the same shape as `getConnections` in metta-demo: an
; accumulator threaded through the recursion, a depth that counts
; down, and `match &self` doing the work. The branching comes from
; MeTTa's non-determinism, so there is no queue to maintain.
;
; The whole search is TWO functions -- getRoutes and searchAtDepth.
; Everything else is display.
;
; BUILT-INS USED (no hand-written list code)
;   union-atom         add a city to the route
;   intersection-atom  has this route been here already?
;   unique-atom        drop duplicate routes
;   collapse           gather non-deterministic results into one list
; ==========================================================

; ----------------------------------------------------------
; 1. The route network
; ----------------------------------------------------------
;; ---------- direct flights ----------
(Flight AddisAbaba Nairobi)
(Flight AddisAbaba Cairo)
(Flight AddisAbaba Dubai)
(Flight AddisAbaba Frankfurt)
(Flight AddisAbaba Johannesburg)
(Flight AddisAbaba Mumbai)

(Flight Nairobi Johannesburg)
(Flight Nairobi Dubai)

(Flight Cairo Istanbul)
(Flight Cairo London)

(Flight Dubai Mumbai)
(Flight Dubai Singapore)
(Flight Dubai London)
(Flight Dubai Istanbul)

(Flight Istanbul Frankfurt)
(Flight Istanbul Delhi)

(Flight London NewYork)
(Flight London Toronto)
(Flight London Paris)

(Flight Paris NewYork)

(Flight Frankfurt NewYork)
(Flight Frankfurt Singapore)

(Flight NewYork Toronto)
(Flight NewYork LosAngeles)
(Flight NewYork SaoPaulo)

(Flight LosAngeles Tokyo)
(Flight LosAngeles Sydney)

(Flight Mumbai Delhi)
(Flight Mumbai Singapore)

(Flight Delhi Bangkok)

(Flight Singapore Bangkok)
(Flight Singapore Sydney)
(Flight Singapore Tokyo)

(Flight Bangkok Beijing)
(Flight Beijing Tokyo)
(Flight Tokyo Sydney)

(Flight SaoPaulo Johannesburg)

;; ---------- high-speed rail ----------
;; London-Paris appears as BOTH a flight and a rail link. That is
;; still ONE edge in the graph, which is why `neighbor` uses `unique`.
(Rail London Paris)
(Rail Paris Frankfurt)

;; ---------- which predicates are actually travelable ----------
;; Without this whitelist the search would happily "travel" from a
;; city into a country name via the attribute facts below.
(RouteType Flight)
(RouteType Rail)

;; ---------- attributes (NOT travelable) ----------
(Country AddisAbaba  Ethiopia)
(Country Nairobi Kenya)
(Country Cairo Egypt)
(Country Johannesburg SouthAfrica)
(Country Dubai UAE)
(Country Istanbul Turkey)
(Country London UnitedKingdom)
(Country Paris France)
(Country Frankfurt Germany)
(Country NewYork USA)
(Country Toronto Canada)
(Country LosAngeles USA)
(Country SaoPaulo Brazil)
(Country Mumbai India)
(Country Delhi India)
(Country Bangkok Thailand)
(Country Singapore Singapore)
(Country Beijing China)
(Country Tokyo Japan)
(Country Sydney Australia)

;; McMurdo Station has no commercial routes in this dataset, so it
;; is deliberately unreachable -- it demonstrates "no route exists".
(Country McMurdo Antarctica)
; ----------------------------------------------------------
; 2. The search
; ----------------------------------------------------------
; $routeSoFar      the route built up so far -- which doubles as the
;                  set of cities already visited
; $currentCity     the city the route has reached
; $remainingDepth  how many more legs this branch may still take
;
; intersection-atom returns () when $nextCity is not already on this
; route, which is how we avoid going in circles.

;;             (AddisAbaba Cairo Istanbul)  Istanbul     Istanbul      0
(= (getRoutes $routeSoFar                   $currentCity $destination $remainingDepth)
   (if (== $currentCity $destination)
       $routeSoFar
       (if (== $remainingDepth 0)
           (empty)
           (match &self ($link Cairo $nextCity) ;; $nextCity -> Istanbul, London
             (if (== (intersection-atom $routeSoFar ($nextCity)) ()) ;; (AddisAbaba Cairo) intersection-atom (Istanbul) => ()
                 (getRoutes (union-atom $routeSoFar ($nextCity)) ;; (AddisAbaba Cairo) union-atom (Istanbul) => (AddisAbaba Cairo Istanbul)
                            $nextCity ;; Istanbul
                            $destination ;; Istanbul
                            (- $remainingDepth 1)) ;; 0
                 (empty))))))

; Try 0 legs, then 1, then 2 ... and stop at the first depth that
; finds anything. That is what makes the answer shortest.

;;                Cairo      Istanbul     1             5
(= (searchAtDepth $startCity $destination $currentDepth $maxDepth)
   (if ( $currentDepth > $maxDepth) ;; Max depth
       ()
       (let $foundRoutes
            (collapse (getRoutes ($startCity) $startCity $destination $currentDepth)) ;; ((AddisAbaba Cairo Istanbul) (AddisAbaba Dubai Istanbul) ...)
         (if (== $foundRoutes ())
             (searchAtDepth $startCity $destination (+ $currentDepth 1) $maxDepth)
             $foundRoutes)))) ;; Routes found

; ----------------------------------------------------------
; 3. Asking the question
; ----------------------------------------------------------
; A city with no links can never be reached, so say so at once
; rather than deepening through every level first.

(= (isStranded $city) ;; AddisAbaba
   (== (collapse (match &self ($link AddisAbaba $neighbourCity) $neighbourCity)) ()))

;; ( Nairobi     
;; Cairo       
;; Dubai       
;; Frankfurt   
;; Johannesburg Mumbai )
(= (shortestRoute $startCity $destination)
   (if (or (isStranded $startCity) (isStranded $destination))
       (NoRoute)
       (let $foundRoutes (searchAtDepth $startCity $destination 0 5)
         (if (== $foundRoutes ()) (NoRoute) (car-atom $foundRoutes)))))































; Everything found at one depth has the same number of legs, so all
; of them are shortest.
(= (allShortestRoutes $startCity $destination)
   (if (or (isStranded $startCity) (isStranded $destination))
       (NoRoute)
       (let $foundRoutes (searchAtDepth $startCity $destination 0 5)
         (if (== $foundRoutes ()) (NoRoute) (unique-atom $foundRoutes)))))

; Which route type(s) join two cities -- for display. $routeType is held
; to a declared RouteType, or the pattern ($routeType $cityA $cityB)
; would also match the (Link ...) atoms built below.
(= (getRouteTypes $cityA $cityB)
   (unique (match &self (RouteType $routeType)
             (superpose ((match &self ($routeType $cityA $cityB) $routeType)
                         (match &self ($routeType $cityB $cityA) $routeType))))))

; ==========================================================
; 4. Make the network undirected
; ----------------------------------------------------------
; !! Every (= ...) definition must appear ABOVE this line. In
; hyperon, definitions written after a `!` statement in the same
; file are loaded TWICE, silently doubling every result.
;
; Routes are stored one way; here we write both directions back
; into the space as (Link a b) atoms.
; ==========================================================

!(collapse (match &self (RouteType $routeType)
             (match &self ($routeType $cityA $cityB)
                (superpose ((add-atom &self (Link $cityA $cityB))
                            (add-atom &self (Link $cityB $cityA)))))))

; ----------------------------------------------------------
; 5. Try it
; ----------------------------------------------------------

!(getRouteTypes London Paris)
; Expected: [Flight, Rail] -- two route types, still ONE edge.

!(shortestRoute AddisAbaba NewYork)
; Expected: (AddisAbaba Frankfurt NewYork) -- 2 legs.

!(shortestRoute AddisAbaba Tokyo)
; Expected: (AddisAbaba Dubai Singapore Tokyo) -- 3 legs.

!(allShortestRoutes London Frankfurt)
; Expected: ((London NewYork Frankfurt) (London Paris Frankfurt))
; Two different 2-leg routes -- both are shortest.

!(shortestRoute Dubai Dubai)
; Expected: (Dubai) -- already there.

!(shortestRoute AddisAbaba McMurdo)
; Expected: (NoRoute) -- McMurdo has no routes at all.

; ----------------------------------------------------------
; 6. Things to try in the session
; ----------------------------------------------------------
; a. Add (Flight AddisAbaba Tokyo), rebuild the link table, and
;    re-run the Tokyo query. It should collapse to
;    (AddisAbaba Tokyo).
; b. Delete the intersection-atom guard in `getRoutes` and re-run.
;    What happens, and why?
; c. Add (RouteType Country) near the top and re-run any search.
;    Trace how a route now "travels" through country names.
; d. `searchAtDepth` stops at the first depth that finds anything. What
;    would `shortestRoute` return if it started at depth 5 and
;    counted DOWN instead?
