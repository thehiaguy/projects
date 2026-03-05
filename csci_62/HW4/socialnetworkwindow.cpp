#include "socialnetworkwindow.h"
#include "ui_socialnetworkwindow.h"
#include <QPushButton>

SocialNetworkWindow::SocialNetworkWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::SocialNetworkWindow)
{
    ui->setupUi(this);

    network_.readUsers("users.txt");
    network_.readPosts("posts.txt");

    loggedin_ = nullptr;
    display_ = nullptr;

    ui->loginErrorButton->hide();

    connect(ui->loginButton,&QPushButton::clicked, this, &SocialNetworkWindow::loginCheck);
}

SocialNetworkWindow::~SocialNetworkWindow()
{
    delete ui;
}

void SocialNetworkWindow::loginCheck(){

    //need to check the name that they gave
    //if name is in the database then go through
    //if name is not in datbase then tell them they can't acccess

    QString name = ui->loginText->toPlainText().trimmed();

    int id = network_.getId(name.toStdString());

    if (id==-1){
        ui->loginErrorButton()->show();
    }
    else{
        ui->loginErrorButton()->hide();

        loggedin_ = network_.getUser(id);
        display_ = loggedin_;

        //Testing
        std::cout<<"Logged in as: "<< loggedin_->getName() <<std::endl;

        //need to hide all the login info now after verifying valid user
        ui->loginButton->hide();
        ui->loginText->hide();
        ui->label->hide();

    }
}
