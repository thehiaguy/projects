#ifndef NETWORK_H
#define NETWORK_H

#include "user.h"
#include <vector>
#include <string>

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



private:
    std::vector<User*>users_;
};



#endif