#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <fstream>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    connect(ui->myButton, &QPushButton::clicked, this, &MainWindow::myButtonClick);

    std::string instructions;
    std::ifstream fin("/Users/zacharypeng/projects/ClickGame/instructions.txt");
    std::getline(fin,instructions);
    std::cout<<"Instructions: "<< instructions<<std::endl;
    ui->instructionlabel->setText(QString::fromStdString(instructions));

}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::myButtonClick(){

    std::cout<<"Hi from myButtonClick"<<std::endl;

    counter.add();//add to counter everytime myBUttonClick was clicked

    ui->label->setText("Number of clicked: " + QString::number(counter.getCount()));

    if(counter.getCount()>=10){
        ui->label->setText("You Win!!");
        ui->myButton->hide();
    }


}
