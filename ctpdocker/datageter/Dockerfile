FROM python:latest

MAINTAINER wangjianhua

WORKDIR /ctpfile/

#在容器中根目录建立目录

COPY requirements.txt /ctpfile/

#拷贝需要的文件进入/ctpfile/

RUN pip install -r requirements.txt　

COPY /py_ctp /usr/local/lib/python3.7/site-packages/py_ctp
# copy py_ctp到目标文件，称为python的自定义包

CMD ["python3", "datacode1.py"]
