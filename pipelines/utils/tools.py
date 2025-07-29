import re

def parse_file_content(text):
    if text == "":
        return {}
    # Pattern to match the format:
    # filename
    # ```
    # content
    # ```
    pattern = r'(?:.*?\n)?([^\n]+)\n```\n(.*?)\n```'
    # re.DOTALL flag to make . match newlines
    matches = re.finditer(pattern, text, re.DOTALL)
    # Create a dictionary to store filename -> content mappings
    result = {}
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2)
        result[filename] = content        
    return result

def parse_stacked_content(text):
    # more precise pattern matching
    pattern = r'(?:^|\n)([^\n]+\.[^\n]+)\n```.*\n((?:(?!```)[\s\S])*)\n```'
    
    # list to store all parsed results
    all_results = []
    
    # find all matches
    matches = re.finditer(pattern, text)
    
    # convert each match to a dictionary and store
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2)
        all_results.append({filename: content})
    
    return all_results

# Test the parser
if __name__ == '__main__':
    # test case 1: simple stacked
    test_input1 = '''file1.txt
```java
content1
multiple lines
here
```
file2.txt
```
content2
more lines
```'''

    # test case 2: stacked with extra text
    test_input2 = '''Some explanation here
file1.py
```
def hello():
    print("Hello")
```

Another explanation
file2.py
```
def world():
    print("World")
```

And more text here
file3.txt
```
Simple text
content
```'''


    test_input3 = '''
**Input:**
```
3 5 2
10 15 20
1 2 5
2 3 8
1 3 7
1 2 3
3 3 2
```

**Output:** (Explanation follows)

```
13
```

**Explanation:**

*   **Request 1 (1, 2, 5):**  Accept. Capacities become: 5, 10, 20.
*   **Request 2 (2, 3, 8):**  Accept. Capacities become: 5, 2, 12.
*   **Request 3 (1, 3, 7):** Reject. Accepting would make server 1's capacity negative.
*   **Request 4 (1, 2, 3):** Accept. Capacities become: 2, -1, 9.
*   **Request 5 (3, 3, 2):** Reject. No more capacity to accept.
Total bandwidth: 5 + 8 = 13.

**The lookahead is key to solving optimally. A greedy approach (always accepting if possible) would NOT be optimal in many cases.** For instance, accepting a large request early might block several smaller, but ultimately more valuable, requests later.

Now, here's the solution:

.meta/solution.cpp
```cpp
#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

struct Request {
    int s, d, b;
};

int solve(int n, int m, int k, vector<int>& capacities, vector<Request>& requests) {
    int total_bandwidth = 0;

    function<int(int, vector<int>, int)> simulate = 
        [&](int request_index, vector<int> current_capacities, int depth) {
        if (request_index >= m || depth > k) {
            return 0;
        }

        int max_simulated_bandwidth = 0;

        // Option 1: Reject the current request
        max_simulated_bandwidth = max(max_simulated_bandwidth, simulate(request_index + 1, current_capacities, depth + 1));

        // Option 2: Accept the current request (if possible)
        Request& req = requests[request_index];
        vector<int> next_capacities = current_capacities;
        bool can_accept = true;

        if (req.s == req.d) {
            if (next_capacities[req.s - 1] >= 2 * req.b) {
                next_capacities[req.s - 1] -= 2 * req.b;
            } else {
                can_accept = false;
            }
        } else {
            if (next_capacities[req.s - 1] >= req.b && next_capacities[req.d - 1] >= req.b) {
                next_capacities[req.s - 1] -= req.b;
                next_capacities[req.d - 1] -= req.b;
            } else {
                can_accept = false;
            }
        }

        if (can_accept) {
            max_simulated_bandwidth = max(max_simulated_bandwidth, req.b + simulate(request_index + 1, next_capacities, depth + 1));
        }
        
        return max_simulated_bandwidth;
    };

    for (int i = 0; i < m; ++i) {
        // Simulate accepting the current request
        vector<int> sim_capacities = capacities;
        Request& req = requests[i];
        bool can_accept_current = true;

         if (req.s == req.d) {
            if (sim_capacities[req.s - 1] >= 2 * req.b) {
                sim_capacities[req.s - 1] -= 2 * req.b;
            } else {
                can_accept_current = false;
            }
        } else {
            if (sim_capacities[req.s - 1] >= req.b && sim_capacities[req.d - 1] >= req.b) {
                sim_capacities[req.s - 1] -= req.b;
                sim_capacities[req.d - 1] -= req.b;
            } else {
                can_accept_current = false;
            }
        }

        int accept_bandwidth = 0;
        if(can_accept_current) {
            accept_bandwidth = req.b + simulate(i + 1, sim_capacities, 1);
        }

        // Simulate rejecting
        int reject_bandwidth = simulate(i + 1, capacities, 1);

        // Make the actual decision
        if (can_accept_current && accept_bandwidth >= reject_bandwidth) {
            total_bandwidth += req.b;
             if (req.s == req.d) {
                capacities[req.s - 1] -= 2 * req.b;
            } else {
                capacities[req.s - 1] -= req.b;
                capacities[req.d - 1] -= req.b;
            }
        }
    }

    return total_bandwidth;
}

int main() {
    int n, m, k;
    cin >> n >> m >> k;

    vector<int> capacities(n);
    for (int i = 0; i < n; ++i) {
        cin >> capacities[i];
    }

    vector<Request> requests(m);
    for (int i = 0; i < m; ++i) {
        cin >> requests[i].s >> requests[i].d >> requests[i].b;
    }

    cout << solve(n, m, k, capacities, requests) << endl;

    return 0;
}
```'''
    print("Test case 1 results:")
    results1 = parse_stacked_content(test_input1)
    for result in results1:
        for filename, content in result.items():
            print(f"\nFilename: {filename}")
            print("Content:")
            print(content)
            
    print("\nTest case 2 results:")
    results2 = parse_stacked_content(test_input2)
    for result in results2:
        for filename, content in result.items():
            print(f"\nFilename: {filename}")
            print("Content:")
            print(content)

    print("\nTest case 3 results:")
    results3 = parse_stacked_content(test_input3)
    for result in results3:
        for filename, content in result.items():
            print(f"\nFilename: {filename}")
            print("Content:")
            print(content)