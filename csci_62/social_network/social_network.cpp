#include <iostream>
#include "network.h"

using namespace std;

int main(int argc, char* argv[]){
    
    if (argc < 2 ){
        cout<< "" <<endl;
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

            break;
        }
        case 2:{

            break;
        }
        case 3:{

            break;
        }
        case 4:{
            
            break;
        }
        
        default:
            cout<<"Thank you for using my Social Network"<<endl;
            return 0;
        }   

    }
    
}