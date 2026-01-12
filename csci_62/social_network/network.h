#ifndef NETWORK_H
#define NETWORK_H

#include "user.h"
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>

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



private:
    //vector of pointer to the user
    std::vector<User*>users_;
};



#endif