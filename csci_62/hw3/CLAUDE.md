# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

```bash
# Build the interactive social network app
make social

# Build all LinkPost tests (test_lpost1–6)
make alltest

# Build all Network tests (test_network1–5)
make alltest2

# Build all Post tests (test_post1–9)
make alltest3

# Build and run a single test
make test_network1 && ./test_network1

# Run command-line autograder tests (requires Python + gradescope_utils)
python3 command_line_tests.py

# Clean build artifacts
make clean
```

## Running the App

```bash
./social users.txt posts.txt
```
The app takes a users file and a posts file as arguments. Menu choices: 1=Add User, 2=Add Friend, 3=Remove Friend, 4=Update (write) Network, 5=Show User's Posts, 6+=Exit.

## Architecture

Three core classes:

- **`Post` / `LinkPost`** (`post.h`, `post.cpp`): `Post` is the base class with `messageId`, `profileId`, `authorId`, `message`, `likes`. `LinkPost` extends it with a `url_` field. `toString()` and `getURL()` are virtual to support polymorphism.

- **`User`** (`user.h`, `user.cpp`): Stores `id_`, `name_`, `year_`, `zip_`, and `friends_` (a `std::set<int>` of friend IDs).

- **`Network`** (`network.h`, `network.cpp`): Top-level graph structure. Holds `users_` (`vector<User*>`) and `posts_` (`vector<vector<Post*>>` indexed by profile ID). Key methods:
  - File I/O: `readUsers`/`writeUsers` (users file format: count, then per-user block with id, name, year, zip, friends), `readPosts`/`writePosts`
  - Graph traversal: `shortestPath` (BFS), `distanceUser`, `suggestFriends`, `groups` (connected components via `dfs`)
  - Post management: `addPost`, `getPosts`, `getPostsString`, `postDisplayString`

- **`social_network.cpp`**: `main()` — interactive CLI driver that loads both files and dispatches menu choices.

## File Formats

**Users file** (e.g., `k4.txt`):
```
<total_users>
<id>
\t<Name>
\t<year>
\t<zip>
\t<friend_id1> <friend_id2> ...
```

**Posts file**: parsed by `readPosts`; posts are stored polymorphically as `Post*` (base) or `LinkPost*` (with URL).

## Test Structure

- `test_lpost*.cpp` — test `LinkPost` behavior
- `test_network*.cpp` — test `Network` graph methods (read from `users.txt`)
- `test_post*.cpp` — test `Post` base class
- `command_line_tests.py` — Gradescope-style integration tests that spawn `./social_network` with piped stdin and check stdout patterns
