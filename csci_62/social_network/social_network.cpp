#include <iostream>
#include "network.h"

using namespace std;

int main(int argc, char* argv[]){
    
    if (argc < 2 ){
        cout<< "Usage: " <<argv[0]<< " <filename>"<<endl;
        return 1;
    }

    Network network;
    network.readUsers(argv[1]);

    int choice;

    while (true){
        cout<<" "<<endl;
        cout<<"-----------------------------"<<endl;
        cout<<"----Zach's Social Network----"<<endl;
        cout<<"-----------------------------"<<endl;
        cout<<"1.   Add User"<<endl;
        cout<<"2.   Add Friend"<<endl;
        cout<<"3.   Remove Friend"<<endl;
        cout<<"4.   Update Netork"<<endl;
        cout<<"5+.  Exit"<<endl;
        cout<<"------------------------------"<<endl;
        cout<<"Please type your choice: ";
        cin>>choice;

        switch (choice){
        case 1:{
            string firstName;
            string lastName;
            int year;
            int zip;
            cout<<"please type out ther people's name in this order:"<<endl;
            cout<<"First name + Last name + DOB + Zip Code"<<endl;
            cin >>firstName >> lastName>>year>>zip; //need to enter the variables to initialize the new user

            string fullName = firstName + " " + lastName;
            int newId = network.numUsers();
            set<int> friends;

            User* newUser = new User(newId, fullName, year, zip, friends);
            network.addUser(newUser);

            cout<<"we have succesfully added "<< fullName <<endl; 
            break;
        }
        case 2:{
            // adding a connection with friend 
            // need to get the names of the person they want to add and their own 
            string s11;
            string s12;
            string s21;
            string s22;
            cout<<"please type out ther people's name in this order:"<<endl;
            cout<<"First name(first person) + Last name(first person) + First name(second person) + Last name(second person)"<<endl;
            cin>>s11>>s12>>s21>>s22;
            
            string s1 = s11 + " " + s12;
            string s2 = s21 + " " + s22;

            int connection = network.addConnection(s1,s2);
            //need to check if the connection was made or it failed
            if(connection == -1){
                cout<<connection;
                cout<< "could not make the connection" << endl;
            }else {
                cout<< "connection was made between "<< s1 <<" and "<< s2<<endl;
            }
            

            break;
        }
        case 3:{
            //removing a connection between two users
            //need to get the name of the two users
            //need to check if they have a connection in the first place
            string s11;
            string s12;
            string s21;
            string s22;
            cout<<"please type out ther people's name in this order:"<<endl;
            cout<<"First name(first person) + Last name(first person) + First name(second person) + Last name(second person)"<<endl;
            cin>>s11>>s12>>s21>>s22;

            string s1 = s11 + " "  + s12;
            string s2 = s21 + " " + s22;

            int deletion = network.deleteConnection(s1,s2);
            if (deletion == -1){
                cout<<"The users are not friends could not complete"<< endl;
            }else{
                 cout<<"Users have been removed as friends"<<endl;
            }
           
            break;
        }
        case 4:{
            //ned to rewrite file

            network.writeUsers(argv[1]);//rewrite the new file into the file we gave
            cout<<"updated file!!"<<endl;
            
            
            break;
        }
        
        default:
            cout<<"Thank you for using my Social Network"<<endl;
            return 0;
        }   

    }

    return 0;
    
}