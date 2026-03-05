#ifndef NETWORK_H
#define NETWORK_H

#include "user.h"
#include "post.h"
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <queue>
#include <algorithm>


class Network{
public:
    Network();

    //pre: takes in id 
    //post: returns pointer to the user
    User* getUser(int id);

    //pre: takes in pointer to the user
    //post: add the user to the database 
    void addUser(User* n);

    //pre: takes in two strings 
    //post: add a friend connection if does not exist yet 
    int addConnection(std::string s1, std::string s2);

    //pre: takes in two strings 
    //post: deletes a friend connection if it exists 
    int deleteConnection(std::string s1, std::string s2);

    //pre: takes in name of user
    //post: returns ID of the user 
    int getId(std::string name);

    //pre: none 
    //post: returns the number of users in network
    int numUsers();

    //pre: none 
    //post: initializes all of the network's info from file
    void readUsers(const char* fname);

    //pre: none
    //post: writes all of the network's information to a file 
    void writeUsers(const char* fname);

    //pre: none 
    //post: return the shortest path of verticies from from to to 
    std::vector<int> shortestPath(int from, int to);

    //pre: pass valid user id and reference variable 
    //post:returns the shortest path to user 
    std::vector<int> distanceUser(int from , int& to, int distance);

    //pre: pass valid user id and score is referene variable 
    //post: return a list of friend suggestion with the highest "score"
    std::vector<int> suggestFriends(int who, int& score);

    //pre:none 
    //post: return list of list of a group of people that are connected to each other but not everyone
    std::vector<std::vector<int>> groups();

    //pre:pass valid user id, tra visited status of users
    //post:recursively visits all the friends from curr
    void dfs(int curr, std::vector<bool> &visited, std::vector<int> &comp);

    //pre:
    //post:
    void addPost(Post* post);

    //pre:
    //post:
    std::vector<Post*> getPosts(int id);

    //pre:
    //post:
    std::string postDisplayString(Post* post);

    //pre:
    //post:
    std::string getPostsString(int profileId, int howMany);

    //pre:
    //post:
    int readPosts(char* fname);

    //pre:
    //post:
    int writePosts(char* fname);

    //pre:
    //post:
   static bool comparePost(Post* n, Post* m);


private:
    //vector of pointer to the user
    std::vector<User*>users_;

    std::vector<std::vector<Post*>>posts_;
};



#endif