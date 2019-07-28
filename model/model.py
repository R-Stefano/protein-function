import tensorflow as tf
import model.utils as utils

class Model(tf.keras.Model):
  def __init__(self):
    super(Model, self).__init__()

    num_labels=1918
    conv_type='1d' #sequential data: [batch, seq, vec]

    self.conv_layers=[
        utils.ConvLayer(conv_type=conv_type, num_filters=32  ,filter_size=9),
        utils.ConvLayer(conv_type=conv_type, num_filters=32  ,filter_size=9, stride=2),
        utils.ConvLayer(conv_type=conv_type, num_filters=64  ,filter_size=9),
        utils.ConvLayer(conv_type=conv_type, num_filters=64  ,filter_size=9, stride=2),
        utils.ConvLayer(conv_type=conv_type, num_filters=128 ,filter_size=9),
        utils.ConvLayer(conv_type=conv_type, num_filters=128 ,filter_size=9, stride=2),
        utils.ConvLayer(conv_type=conv_type, num_filters=256 ,filter_size=9),
        utils.ConvLayer(conv_type=conv_type, num_filters=512 ,filter_size=9)
    ]

    #TRANSFORMER
    head_vecs=64
    num_heads=8
    d_model=num_heads*head_vecs # 512=8*64
    dff=2048
    self.self_attention_layers=[
        utils.TransformerLayer(d_model=d_model, num_heads=num_heads, dff=dff)
    ]

    #FLAT
    self.flat=tf.keras.layers.Flatten()

    #FC
    self.fc_layers=[
      tf.keras.layers.Dense(1024, activation='relu'),
      tf.keras.layers.Dense(num_labels, activation='sigmoid')
    ]
    

  def call(self, x, training):
    print('Input shape:', x.shape)

    for i, layer in enumerate(self.conv_layers):
        x=layer(x)
        print('conv_{}: {}'.format(i, x.shape))
    
    #Positional encoding
    x += utils.positionalEncoding(x.shape[1], x.shape[-1])

    for i, layer in enumerate(self.self_attention_layers):
        x=layer(x, training)
        print('trans_{}: {}'.format(i, x.shape))

    x=tf.math.reduce_mean(x, axis=1)
    print('projected transformer output:', x.shape)

    for i,layer in enumerate(self.fc_layers):
      x=layer(x)
      print('fc_{}: {}'.format(i, x.shape))
    return x