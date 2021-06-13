#ReadME

Inlucene is a sql to elastic json converter which converts you sql query to lucene(elastic json) query and fetch the data from elastic search.
-- you dont need to write direct json , you just have to write sql query and it parse that query to transform lucene.--
Python 3.6 is required and and django framekwork(python) is used .

Additional step:
create a config.py file in converter folder and place the ip/dns of elastic search like this.

/******
config={
IP:'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
}
*******/<br/>

Note: This is pretty much basic but very effective .<br/>
1.compile: compile button translate sql to valid elsatic json<br/>
2.compile and run: ths button traslate to json and fetch the data from elastic and show in a tabular format on UI..<br/>

![image](https://user-images.githubusercontent.com/50418448/121794383-40ec0d00-cc25-11eb-96fc-ab3fa5de1bbb.png)
![image](https://user-images.githubusercontent.com/50418448/121794422-7f81c780-cc25-11eb-8bd6-07888de4716f.png)
