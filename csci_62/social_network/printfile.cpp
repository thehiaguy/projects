#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

void printFile (const char* fname){
    std::ifstream file(fname);

    char c;
    while (file.get(c)){
        if (c == ' '){
            std::cout<< '.';
        }
        else if (c == '\t'){
            std::cout<< '>';
        }
        else{
            std::cout<< c;
        }
    }

    file.close();
}


int main(){
    printFile("users.txt");
    return 0;
}